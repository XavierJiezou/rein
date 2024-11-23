# dataset config
_base_ = [
    "../_base_/datasets/gf12ms_whu_gf2.py",
    "../_base_/default_runtime.py",
    "../_base_/models/convnext_dinov2_maskformer.py"
]

num_classes = 2

model = dict(
    data_preprocessor=dict(
        type="SegDataPreProcessor",
        mean=[123.675, 116.28, 103.53],
        std=[58.395, 57.12, 57.375],
        size=(256, 256),
        bgr_to_rgb=True,
        pad_val=0,
        seg_pad_val=255,
    ),
    backbone=dict(
        img_size=256,
        convnext_config=dict(
            type="AdapterConvNeXtBlock",
            embed_dim=1024,
            rank_type="high", # low or high 
            rank_scale=8, # 1, 2, 4, 8 
            alpha = 1,  # 1, 2, 4, 8 or nn.Parameter(data=torch.ones(embed_dim))
            act_layer = "silu", # nn.GELU or nn.SiLU
            has_conv = True,
            has_proj = True,
            drop_prob=0, 
        ),
        init_cfg=dict(
            type="Pretrained",
            checkpoint="checkpoints/dinov2_converted_256x256.pth",
        ),
    ),
    decode_head=dict(
        num_classes=num_classes,
        loss_cls=dict(
            type="mmdet.CrossEntropyLoss",  # 解决类别不均衡
            use_sigmoid=False,
            loss_weight=2.0,
            reduction="mean",
            class_weight=[1.0] * num_classes + [0.1],  # [1, 1, 0.1]
        ),
    ),
    test_cfg=dict(),
)

# AdamW optimizer, no weight decay for position embedding & layer norm
# in backbone
embed_multi = dict(lr_mult=1.0, decay_mult=0.0)
optim_wrapper = dict(
    constructor="PEFTOptimWrapperConstructor",
    optimizer=dict(
        type="AdamW", lr=0.0001, weight_decay=0.05, eps=1e-8, betas=(0.9, 0.999)
    ),
    paramwise_cfg=dict(
        custom_keys={
            "norm": dict(decay_mult=0.0),
            "query_embed": embed_multi,
            "level_embed": embed_multi,
            "learnable_tokens": embed_multi,
            "reins.scale": embed_multi,
        },
        norm_decay_mult=0.0,
    ),
)
param_scheduler = [
    dict(type="PolyLR", eta_min=0, power=0.9, begin=0, end=40000, by_epoch=False)
]

# training schedule for 160k
# train_cfg = dict(type="IterBasedTrainLoop", max_iters=40000, val_interval=10000)
train_cfg = dict(type="IterBasedTrainLoop", max_iters=40000, val_interval=4000)
val_cfg = dict(type="ValLoop")
test_cfg = dict(type="TestLoop")
default_hooks = dict(
    timer=dict(type="IterTimerHook"),
    logger=dict(type="LoggerHook", interval=4000, log_metric_by_epoch=False),
    param_scheduler=dict(type="ParamSchedulerHook"),
    checkpoint=dict(
        type="CheckpointHook",
        by_epoch=False,
        interval=4000,
        max_keep_ckpts=1,
        save_best=["mIoU"],
        rule="greater",
    ),
    sampler_seed=dict(type="DistSamplerSeedHook"),
    visualization=dict(type="SegVisualizationHook"),
)