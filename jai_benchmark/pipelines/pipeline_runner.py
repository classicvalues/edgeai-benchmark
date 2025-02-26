# Copyright (c) 2018-2021, Texas Instruments
# All Rights Reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import sys
import functools
import itertools
import warnings
import copy
import traceback

try:
    import onnx
except:
    #warnings.warn('onnx could not be imported - this is not required for inference, but may be required for import')
    pass

try:
    from onnxsim import simplify
except:
    #warnings.warn('onnxsim could not be imported - this is not required for inference, but may be required for import')
    pass

from .accuracy_pipeline import *
from .. import utils
from jai_benchmark import preprocess

#from prototxt_parser.prototxt import parse as prototxt_parse

class PipelineRunner():
    def __init__(self, settings, pipeline_configs):
        self.settings = settings
        for model_id, pipeline_config in pipeline_configs.items():
            # set model_id in each config
            pipeline_config['session'].set_param('model_id', model_id)
            session = pipeline_config['session']
            # call initialize() on each pipeline_config so that run_dir,
            # artifacts folder and such things are initialized
            session.initialize()
            # get the meta params if it is present and populate model_info - this is just for information
            # commenting out, as this add additional python package dependency
            # od_meta_names_key = 'object_detection:meta_layers_names_list'
            # runtime_options = session.get_param('runtime_options')
            # meta_path = runtime_options.get(od_meta_names_key, None)
            # if meta_path is not None and isinstance(meta_path, str) and os.path.splitext(meta_path)[-1] == '.prototxt':
            #     meta_info = self._parse_prototxt(meta_path)
            #     model_info = pipeline_config.get('model_info', {})
            #     model_info[od_meta_names_key] = meta_info
            # #
        #
        # short list a set of models based on the wild card given in model_selection
        pipelines_selected = {}
        for model_id, pipeline_config in pipeline_configs.items():
            if self._check_model_selection(self.settings, pipeline_config):
                pipelines_selected.update({model_id: pipeline_config})
            #
        #
        if settings.config_range is not None:
            pipelines_selected = dict(itertools.islice(pipelines_selected.items(), *settings.config_range))
        #
        if settings.model_transformation_dict is not None:
            pipelines_selected = self.model_transformation(settings, pipelines_selected)
        #
        self.pipeline_configs = pipelines_selected

    def run(self):
        if self.settings.parallel_devices is not None:
            return self._run_pipelines_parallel()
        else:
            return self._run_pipelines_sequential()
        #

    def _run_pipelines_sequential(self):
        # get the cwd so that we can continue even if exception occurs
        cwd = os.getcwd()
        results_list = []
        total = len(self.pipeline_configs)
        for pipeline_id, pipeline_config in enumerate(self.pipeline_configs.values()):
            os.chdir(cwd)
            description = f'{pipeline_id+1}/{total}' if total > 1 else ''
            result = self._run_pipeline(self.settings, pipeline_config, description=description)
            results_list.append(result)
        #
        return results_list

    def _run_pipelines_parallel(self):
        # get the cwd so that we can continue even if exception occurs
        assert isinstance(self.settings.parallel_devices, list), \
            'parallel_devices must be None or a list of integers (GPU/CUDA devices)'

        cwd = os.getcwd()
        num_devices = len(self.settings.parallel_devices)
        description = 'TASKS'
        parallel_exec = utils.ParallelRun(num_processes=num_devices, parallel_devices=self.settings.parallel_devices,
                                          desc=description)
        for pipeline_index, pipeline_config in enumerate(self.pipeline_configs.values()):
            os.chdir(cwd)
            run_pipeline_bound_func = functools.partial(self._run_pipeline, self.settings, pipeline_config,
                                                        description='')
            parallel_exec.enqueue(run_pipeline_bound_func)
        #
        results_list = parallel_exec.run()
        return results_list

    # this function cannot be an instance method of PipelineRunner, as it causes an
    # error during pickling, involved in the launch of a process is parallel run. make it classmethod
    @classmethod
    def _run_pipeline(cls, settings_in, pipeline_config_in, description=''):
        # create a copy to avoid issues due to running multiple models
        pipeline_config = copy.deepcopy(pipeline_config_in)
        # note that this basic_settings() copies only the basic settings.
        # sometimes, there is no need to copy the entire settings which includes the dataset_cache
        settings = settings_in.basic_settings()

        # capture cwd - to set it later
        cwd = os.getcwd()

        result = {}
        try:
            if settings.pipeline_type == constants.PIPELINE_ACCURACY:
                # use with statement, so that the logger and other file resources are cleaned up
                with AccuracyPipeline(settings, pipeline_config) as accuracy_pipeline:
                    accuracy_result = accuracy_pipeline(description)
                    result.update(accuracy_result)
                #
            elif settings.pipeline_type == constants.PIPELINE_SOMETHING:
                # this is just an example of how other pipelines can be implemented.
                # 'something' used here is not real and it is not supported
                with SomethingPipeline(settings, pipeline_config) as something_pipeline:
                    something_result = something_pipeline(description)
                    result.update(something_result)
                #
            else:
                assert False, f'unknown pipeline: {settings.pipeline_type}'
            #
        except Exception as e:
            print(f'\n{str(e)}')
            traceback.print_exc()
        #
        # make sure we are in cwd when we return.
        os.chdir(cwd)
        return result

    def _str_match_any(self, k, x_list):
        match_any = any([(k in x) for x in x_list])
        return match_any

    def _str_match_plus(self, ks, x_list):
        ks = ks.split('+')
        match_fully = all([self._str_match_any(k,x_list) for k in ks])
        return match_fully

    def _str_match_plus_any(self, keywords, search_list):
        any_match_fully = any([self._str_match_plus(kw, search_list) for kw in keywords])
        return any_match_fully

    def _check_model_selection(self, settings, pipeline_config):
        model_path = pipeline_config['session'].get_param('model_path')
        model_id = pipeline_config['session'].get_param('model_id')
        model_path0 = model_path[0] if isinstance(model_path, (list,tuple)) else model_path
        model_type = pipeline_config['session'].get_param('model_type')
        model_type = model_type or os.path.splitext(model_path0)[1][1:]
        shortlist_model = True
        if settings.model_shortlist is not None:
            model_shortlist = utils.as_list(settings.model_shortlist)
            shortlist_model = self._str_match_plus_any(model_shortlist, (model_path0,model_id,model_type))
        #
        if not shortlist_model:
            return False
        #
        selected_model = True
        if settings.model_selection is not None:
            model_selection = utils.as_list(settings.model_selection)
            selected_model = self._str_match_plus_any(model_selection, (model_path0,model_id,model_type))
        #
        if settings.model_exclusion is not None:
            model_exclusion = utils.as_list(settings.model_exclusion)
            excluded_model = self._str_match_plus_any(model_exclusion, (model_path0,model_id,model_type))
            selected_model = selected_model and (not excluded_model)
        #
        if settings.task_selection is not None:
            task_selection = utils.as_list(settings.task_selection)
            if pipeline_config['task_type'] not in task_selection:
                selected_model = False
            #
        #
        # calibration_dataset = pipeline_config['calibration_dataset']
        # if settings.run_import and calibration_dataset is None:
        #     if settings.verbose:
        #         warnings.warn(f'settings.run_import was set, but calibration_dataset={calibration_dataset}, removing model {model_id}:{model_path0}')
        #     #
        #     selected_model = False
        # #
        # input_dataset = pipeline_config['input_dataset']
        # if settings.run_inference and input_dataset is None:
        #     if settings.verbose:
        #         warnings.warn(f'settings.run_inference was set, but input_dataset={input_dataset}, removing model {model_id}:{model_path0}')
        #     #
        #     selected_model = False
        # #
        return selected_model

    def model_transformation(self, settings, pipeline_configs_in):
        if 'input_sizes' not in settings.model_transformation_dict:
            return
        #
        input_sizes = settings.model_transformation_dict['input_sizes']

        pipeline_configs_out = {}
        for size_id, input_size in enumerate(input_sizes):
            # modify a pipeline so that all the models use fixed input size
            # other modifications can also be defined here.
            warning_string = f'Changing input size to {input_size}.\n' \
                             f'The accuracies reported may be wrong as input_size is changed from the default value.'
            print(warning_string)

            for pipeline_id, pipeline_config_in in pipeline_configs_in.items():
                # start with fresh set of configs - not the one modified in earlier iteration
                pipeline_config = copy.deepcopy(pipeline_config_in)
                # start modifying the model for the given input resolution
                preproc_stge = pipeline_config['preprocess']
                preproc_transforms = preproc_stge.transforms
                for tidx, trans in enumerate(preproc_transforms):
                    if isinstance(trans, preprocess.ImageResize):
                        trans = preprocess.ImageResize(input_size)
                        preproc_stge.set_param('resize', input_size)
                    elif isinstance(trans, preprocess.ImageCenterCrop):
                        trans = preprocess.ImageCenterCrop(input_size)
                        preproc_stge.set_param('crop', input_size)
                    #
                    preproc_transforms[tidx] = trans
                #
                # generate temporary ONNX  model based on fixed resolution
                model_path = pipeline_config['session'].peek_param('model_path')
                # supported only for onnx
                if isinstance(model_path, (list,tuple)) or os.path.splitext(model_path)[-1] != '.onnx':
                    continue
                #
                #print("=" * 64)
                #print("src model path :{}".format(model_path))

                # create a new model_id for the modified model
                new_model_id = pipeline_id[:-1] + str(1+size_id)
                pipeline_config['session'].set_param('model_id', new_model_id)

                # set model_path with the desired size so that the run_dir also will have that size
                # this step is just dummy - the model with the modified name doesn't exist at this point
                model_path_tmp = model_path.replace(".onnx", "_{}x{}.onnx".format(input_size, input_size))
                pipeline_config['session'].set_param('model_path', model_path_tmp)

                # initialize must be called to re-create run_dir and artifacts_folder for this new model_id
                # it is possible that initialize() must have been called before - we need to set run_dir to None to re-create it
                pipeline_config['session'].set_param('run_dir', None)
                pipeline_config['session'].initialize()

                # run_dir must have been created now
                run_dir = pipeline_config['session'].get_param('run_dir')
                model_folder = pipeline_config['session'].get_param('model_folder')

                # now set the final model_path
                model_path_out = os.path.join(model_folder, os.path.basename(model_path_tmp))
                pipeline_config['session'].set_param('model_path', model_path_out)

                # create the modified onnx model with the required input size
                # if the run_dir or the packaged (.tar.gz) artifact is available, this will be skipped
                tarfile_name = run_dir + '.tar.gz'
                linkfile_name = run_dir + '.tar.gz.link'
                if (not os.path.exists(run_dir)) and (not os.path.exists(tarfile_name)) and (not os.path.exists(linkfile_name)):
                    onnx_model = onnx.load(model_path)
                    input_name_shapes = self.get_input_shape_onnx(onnx_model)
                    assert len(input_name_shapes) == 1
                    input_name = None
                    for k, v in input_name_shapes.items():
                        input_name = k
                    #
                    out_name_shapes = self.get_output_shape_onnx(onnx_model)

                    # variable shape model
                    input_var_shapes = {input_name: ['b', 3, 'w', 'h']}

                    # create first varibale shape model
                    onnx_model = utils.onnx_update_model_dims(onnx_model, input_var_shapes, out_name_shapes)
                    input_name_shapes[input_name] = [1, 3, input_size, input_size]
                    # change to fixed shape model
                    try:
                        onnx_model, check = simplify(onnx_model, skip_shape_inference=False, input_shapes=input_name_shapes)
                    except:
                        warnings.warn(f'please install onnx-simplifier : onnxsim.simplify() - changing the size of {model_path} did not work - skipping')
                        continue
                    #
                    # save model in model_folder
                    os.makedirs(model_folder, exist_ok=True)
                    #print("saving modified model :{}".format(model_path_out))
                    onnx.save(onnx_model, model_path_out)
                    #onnx.shape_inference.infer_shapes_path(model_path_out, model_path_out)
                #
                pipeline_configs_out.update({new_model_id: pipeline_config})
            #
        #
        return pipeline_configs_out


    def get_input_shape_onnx(self, onnx_model, num_inputs=1):
        input_shape = {}
        for input_idx in range(num_inputs):
            input_i = onnx_model.graph.input[input_idx]
            name = input_i.name
            shape = [dim.dim_value for dim in input_i.type.tensor_type.shape.dim]
            input_shape.update({name: shape})
        #
        return input_shape


    def get_output_shape_onnx(self, onnx_model, num_outputs=1):
        output_shape = {}
        num_outputs = 1
        for output_idx in range(num_outputs):
            output_i = onnx_model.graph.output[output_idx]
            name = output_i.name
            shape = [dim.dim_value for dim in output_i.type.tensor_type.shape.dim]
            output_shape.update({name:shape})
        #
        return output_shape


    # def _parse_prototxt(self, prototxt_filename):
    #     try:
    #         with open(prototxt_filename) as fp:
    #             file_lines = fp.readlines()
    #             prototxt_lines = []
    #             for line in file_lines:
    #                 line = line.rstrip()
    #                 # prototxt_parser doesnt line comments - remove them
    #                 line_out = ''
    #                 for c in line:
    #                     if c == '#':
    #                         break
    #                     else:
    #                         line_out += c
    #                     #
    #                 #
    #                 prototxt_lines.append(line_out)
    #             #
    #             prototxt_str = '\n'.join(prototxt_lines)
    #             meta_info = prototxt_parse(prototxt_str)
    #         #
    #     except:
    #         meta_info = None
    #     #
    #     return meta_info
