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

import cv2
from .. import constants, utils, datasets, preprocess, sessions, postprocess, metrics


def get_configs(settings, work_dir):
    # get the sessions types to use for each model type
    session_name_to_type_dict = sessions.get_session_name_to_type_dict()
    onnx_session_type = session_name_to_type_dict[settings.session_type_dict[constants.MODEL_TYPE_ONNX]]
    tflite_session_type = session_name_to_type_dict[settings.session_type_dict[constants.MODEL_TYPE_TFLITE]]
    mxnet_session_type = session_name_to_type_dict[settings.session_type_dict[constants.MODEL_TYPE_MXNET]]

    # get the session cfgs to be used for float models
    session_name_to_cfg_dict = settings.get_session_name_to_cfg_dict(is_qat=False)
    onnx_session_cfg = session_name_to_cfg_dict[settings.session_type_dict[constants.MODEL_TYPE_ONNX]]
    tflite_session_cfg = session_name_to_cfg_dict[settings.session_type_dict[constants.MODEL_TYPE_TFLITE]]
    mxnet_session_cfg = session_name_to_cfg_dict[settings.session_type_dict[constants.MODEL_TYPE_MXNET]]

    # get the session cfgs to be used for qat models
    session_name_to_cfg_dict_qat = settings.get_session_name_to_cfg_dict(is_qat=True)
    onnx_session_cfg_qat = session_name_to_cfg_dict_qat[settings.session_type_dict[constants.MODEL_TYPE_ONNX]]
    tflite_session_cfg_qat = session_name_to_cfg_dict_qat[settings.session_type_dict[constants.MODEL_TYPE_TFLITE]]
    mxnet_session_cfg_qat = session_name_to_cfg_dict_qat[settings.session_type_dict[constants.MODEL_TYPE_MXNET]]

    # configs for each model pipeline
    cityscapes_cfg = {
        'pipeline_type': settings.pipeline_type,
        'verbose': settings.verbose,
        'target_device': settings.target_device,
        'run_import': settings.run_import,
        'run_inference': settings.run_inference,
        'calibration_dataset': settings.dataset_cache['cityscapes']['calibration_dataset'],
        'input_dataset': settings.dataset_cache['cityscapes']['input_dataset'],
    }

    ade20k_cfg = {
        'pipeline_type': settings.pipeline_type,
        'verbose': settings.verbose,
        'target_device': settings.target_device,
        'run_import': settings.run_import,
        'run_inference': settings.run_inference,
        'calibration_dataset': settings.dataset_cache['ade20k']['calibration_dataset'],
        'input_dataset': settings.dataset_cache['ade20k']['input_dataset'],
    }

    ade20k_cfg_class32 = {
        'pipeline_type': settings.pipeline_type,
        'verbose': settings.verbose,
        'target_device': settings.target_device,
        'run_import': settings.run_import,
        'run_inference': settings.run_inference,
        'calibration_dataset': settings.dataset_cache['ade20k_class32']['calibration_dataset'],
        'input_dataset': settings.dataset_cache['ade20k_class32']['input_dataset'],
    }

    pascal_voc_cfg = {
        'pipeline_type': settings.pipeline_type,
        'verbose': settings.verbose,
        'target_device': settings.target_device,
        'run_import': settings.run_import,
        'run_inference': settings.run_inference,
        'calibration_dataset': settings.dataset_cache['voc2012']['calibration_dataset'],
        'input_dataset': settings.dataset_cache['voc2012']['input_dataset'],
    }

    common_session_cfg = dict(work_dir=work_dir, target_device=settings.target_device)

    postproc_segmentation_onnx = settings.get_postproc_segmentation_onnx()
    postproc_segmenation_tflite = settings.get_postproc_segmentation_tflite(with_argmax=False)

    pipeline_configs = {
        #################################################################
        #       ONNX MODELS
        #################mlperf models###################################
        # jai-pytorch: segmentation - deeplabv3lite_mobilenetv2_tv_768x384_20190626-085932 expected_metric: 69.13% mean-iou
        'vseg-16-100-0':utils.dict_update(cityscapes_cfg,
            preprocess=settings.get_preproc_jai((384,768), (384,768), backend='cv2', interpolation=cv2.INTER_AREA),
            session=onnx_session_type(**common_session_cfg, **onnx_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/cityscapes/jai-pytorch/deeplabv3lite_mobilenetv2_tv_768x384_20190626-085932_opset11.onnx'),
            postprocess=postproc_segmentation_onnx,
            model_info=dict(metric_reference={'accuracy_mean_iou%':69.13})
        ),
        # jai-pytorch: segmentation - fpnlite_aspp_mobilenetv2_tv_768x384_20200120-135701 expected_metric: 70.48% mean-iou
        'vseg-16-101-0':utils.dict_update(cityscapes_cfg,
            preprocess=settings.get_preproc_jai((384,768), (384,768), backend='cv2', interpolation=cv2.INTER_AREA),
            session=onnx_session_type(**common_session_cfg, **onnx_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/cityscapes/jai-pytorch/fpnlite_aspp_mobilenetv2_tv_768x384_20200120-135701_opset11.onnx'),
            postprocess=postproc_segmentation_onnx,
            model_info=dict(metric_reference={'accuracy_mean_iou%':70.48})
        ),
        # jai-pytorch: segmentation - unetlite_aspp_mobilenetv2_tv_768x384_20200129-164340 expected_metric: 68.97% mean-iou
        'vseg-16-102-0':utils.dict_update(cityscapes_cfg,
            preprocess=settings.get_preproc_jai((384,768), (384,768), backend='cv2', interpolation=cv2.INTER_AREA),
            session=onnx_session_type(**common_session_cfg, **onnx_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/cityscapes/jai-pytorch/unetlite_aspp_mobilenetv2_tv_768x384_20200129-164340_opset11.onnx'),
            postprocess=postproc_segmentation_onnx,
            model_info=dict(metric_reference={'accuracy_mean_iou%':68.97})
        ),
        # jai-pytorch: segmentation - fpnlite_aspp_regnetx800mf_768x384_20200911-144003 expected_metric: 72.01% mean-iou
        'vseg-16-103-0':utils.dict_update(cityscapes_cfg,
            preprocess=settings.get_preproc_jai((384,768), (384,768), backend='cv2', interpolation=cv2.INTER_AREA),
            session=onnx_session_type(**common_session_cfg, **onnx_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/cityscapes/jai-pytorch/fpnlite_aspp_regnetx800mf_768x384_20200911-144003_opset11.onnx'),
            postprocess=postproc_segmentation_onnx,
            model_info=dict(metric_reference={'accuracy_mean_iou%':72.01})
        ),
        # jai-pytorch: segmentation - fpnlite_aspp_regnetx1.6gf_1024x512_20200914-132016 expected_metric: 75.84% mean-iou
        'vseg-16-104-0':utils.dict_update(cityscapes_cfg,
            preprocess=settings.get_preproc_jai((512,1024), (512,1024), backend='cv2', interpolation=cv2.INTER_AREA),
            session=onnx_session_type(**common_session_cfg, **onnx_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/cityscapes/jai-pytorch/fpnlite_aspp_regnetx1.6gf_1024x512_20200914-132016_opset11.onnx'),
            postprocess=postproc_segmentation_onnx,
            model_info=dict(metric_reference={'accuracy_mean_iou%':75.84})
        ),
        # jai-pytorch: segmentation - fpnlite_aspp_regnetx3.2gf_1536x768_20200915-092738 expected_metric: 78.90% mean-iou
        'vseg-16-105-0':utils.dict_update(cityscapes_cfg,
            preprocess=settings.get_preproc_jai((768,1536), (768,1536), backend='cv2', interpolation=cv2.INTER_AREA),
            session=onnx_session_type(**common_session_cfg, **onnx_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/cityscapes/jai-pytorch/fpnlite_aspp_regnetx3.2gf_1536x768_20200915-092738_opset11.onnx'),
            postprocess=postproc_segmentation_onnx,
            model_info=dict(metric_reference={'accuracy_mean_iou%':78.90})
        ),
        # torchvision: segmentation - torchvision deeplabv3-resnet50 - expected_metric: 73.5% MeanIoU.
        'vseg-16-300-0':utils.dict_update(cityscapes_cfg,
            preprocess=settings.get_preproc_onnx((520,1040), (520,1040), backend='cv2'),
            session=onnx_session_type(**common_session_cfg, **onnx_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/cityscapes/torchvision/deeplabv3_resnet50_1040x520_20200901-213517_opset11.onnx'),
            postprocess=postproc_segmentation_onnx,
            model_info=dict(metric_reference={'accuracy_mean_iou%':73.5})
        ),
        # torchvision: segmentation - torchvision fcn-resnet50 - expected_metric: 71.6% MeanIoU.
        'vseg-16-301-0':utils.dict_update(cityscapes_cfg,
            preprocess=settings.get_preproc_onnx((520,1040), (520,1040), backend='cv2'),
            session=onnx_session_type(**common_session_cfg, **onnx_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/cityscapes/torchvision/fcn_resnet50_1040x520_20200902-153444_opset11.onnx'),
            postprocess=postproc_segmentation_onnx,
            model_info=dict(metric_reference={'accuracy_mean_iou%':71.6})
        ),
        #################################################################
        #       TFLITE MODELS
        #################mlperf models###################################
        #mlperf: ade20k-segmentation (32 class) - deeplabv3_mnv2_ade20k_float - expected_metric??
        'vseg-18-010-0':utils.dict_update(ade20k_cfg_class32,
            preprocess=settings.get_preproc_tflite((512, 512), (512, 512), mean=(123.675, 116.28, 103.53), scale=(0.017125, 0.017507, 0.017429), backend='cv2'),
            session=tflite_session_type(**common_session_cfg, **tflite_session_cfg,
                 model_path=f'{settings.modelzoo_path}/vision/segmentation/ade20k_class32/mlperf/deeplabv3_mnv2_ade20k_float.tflite'),
            postprocess=postproc_segmenation_tflite,
            model_info=dict(metric_reference={'accuracy_mean_iou%':54.8})
        ),
        #################tensorflow models###################################
        #tensorflow-deeplab-ade20k-segmentation- deeplabv3_mnv2_ade20k_train_2018_12_03 - expected_metric: 32.04% MeanIoU.
        'vseg-17-400-0':utils.dict_update(ade20k_cfg,
            preprocess=settings.get_preproc_tflite((512, 512), (512, 512), mean=(123.675, 116.28, 103.53), scale=(0.017125, 0.017507, 0.017429), backend='cv2'),
            session=tflite_session_type(**common_session_cfg, **tflite_session_cfg,
                 model_path=f'{settings.modelzoo_path}/vision/segmentation/ade20k/tf1-models/deeplabv3_mnv2_ade20k_train_2018_12_03_512x512.tflite'),
            postprocess=postproc_segmenation_tflite,
            model_info=dict(metric_reference={'accuracy_mean_iou%':32.04})
        ),
        # tensorflow-deeplab-cityscapes-segmentation- deeplabv3_mnv2_cityscapes_train - expected_metric: 73.57% MeanIoU.
        'vseg-16-400-0': utils.dict_update(cityscapes_cfg,
            preprocess=settings.get_preproc_tflite((1024, 2048), (1024, 2048), mean=(127.5, 127.5, 127.5), scale=(1/127.5, 1/127.5, 1/127.5), backend='cv2'),
            session=tflite_session_type(**common_session_cfg, **tflite_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/cityscapes/tf1-models/deeplabv3_mnv2_cityscapes_train_1024x2048.tflite'),
            postprocess=postproc_segmenation_tflite,
            model_info=dict(metric_reference={'accuracy_mean_iou%':73.57})
        ),
        # tensorflow-deeplab-pascal-voc-segmentation- deeplabv3_mnv2_dm05_pascal_trainaug - expected_metric: 70.19% MeanIoU.
        'vseg-19-400-0': utils.dict_update(pascal_voc_cfg, #pascalvoc2012 deeplab
            preprocess=settings.get_preproc_tflite((512, 512), (512, 512), mean=(127.5, 127.5, 127.5), scale=(1/127.5, 1/127.5, 1/127.5), backend='cv2'),
            session=tflite_session_type(**common_session_cfg, **tflite_session_cfg,
                model_path=f'{settings.modelzoo_path}/vision/segmentation/voc2012/tf1-models/deeplabv3_mnv2_dm05_pascal_trainaug_512x512.tflite'),
            postprocess=postproc_segmenation_tflite,
            model_info=dict(metric_reference={'accuracy_mean_iou%':70.19})
       ),
        # tensorflow-deeplab-pascal-voc-segmentation- deeplabv3_mnv2_pascal_train_aug - expected_metric: 77.33% MeanIoU.
        'vseg-19-401-0': utils.dict_update(pascal_voc_cfg,  # pascalvoc2012 deeplab
            preprocess=settings.get_preproc_tflite((512, 512), (512, 512), mean=(127.5, 127.5, 127.5), scale=(1/127.5, 1/127.5, 1/127.5), backend='cv2'),
            session=tflite_session_type(**common_session_cfg, **tflite_session_cfg,
               model_path=f'{settings.modelzoo_path}/vision/segmentation/voc2012/tf1-models/deeplabv3_mnv2_pascal_train_aug_512x512.tflite'),
            postprocess=postproc_segmenation_tflite,
            model_info=dict(metric_reference={'accuracy_mean_iou%':77.33})
        ),
    }
    return pipeline_configs

