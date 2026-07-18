"""Device-only LLM scheduling with optional non-LLM GPU support."""

from __future__ import annotations

from typing import Any, Mapping

from tools.total_field.w7tp_field_application_runtime import device_llm_execution_policy


LLM_WORKLOADS = frozenset({"INFERENCE", "LLM", "LLM_INFERENCE", "GENERATIVE_AI"})
SERVER_GPU_WORKLOADS = frozenset({"AUDIO_VIDEO", "BATCH", "MEDIA_TRANSCODE", "NON_LLM_INFERENCE"})


def select_execution_policy(
    gpu_probe: Mapping[str, Any] | None = None,
    *,
    workload: str = "INTENT_FIELD",
) -> dict[str, Any]:
    probe = dict(gpu_probe or {})
    workload = str(workload).strip().upper()
    gpu_usable = probe.get("usable") is True and probe.get("owner_verified") is True
    llm_workload = workload in LLM_WORKLOADS
    gpu_selected = not llm_workload and gpu_usable and workload in SERVER_GPU_WORKLOADS
    device_policy = device_llm_execution_policy()
    return {
        "schema_version": "W7TP-CPU-GPU-POLICY/1.1",
        "workload": workload,
        "workload_class": "LLM" if llm_workload else "NON_LLM",
        "execution_mode": "USER_DEVICE_LLM" if llm_workload else ("GPU_SUPPORT" if gpu_selected else "CPU_BASELINE"),
        "execution_location": "USER_DEVICE_ONLY" if llm_workload else "TAIJI01_OR_VERIFIED_NON_LLM_WORKER",
        "cpu_complete": True,
        "gpu_optional": True,
        "gpu_selected": gpu_selected,
        "gpu_authority": "CANDIDATE_EXECUTION_ONLY",
        "total_field_authority": "TAIJI01_LOCAL_ONLY",
        "server_llm_execution": "BLOCK",
        "server_role": device_policy["server_role"],
        "on_gpu_interruption": "USER_DEVICE_LOCAL_QUEUE_OR_USER_DECISION" if llm_workload else "CPU_FALLBACK_OR_QUEUE",
        "cloud_fallback": "BLOCK",
        "minimum_data": device_policy["server_input"] if llm_workload else "DEIDENTIFIED_NON_LLM_WORK_PACKET_ONLY",
        "raw_prompt_upload": "BLOCK",
        "model_context_upload": "BLOCK",
    }


def nvidia_tool_decision(gpu_probe: Mapping[str, Any] | None = None) -> dict[str, str]:
    probe = dict(gpu_probe or {})
    return {
        "windows_driver_wsl_integration": "REQUIRED_READ_ONLY_VERIFY",
        "linux_display_driver_in_wsl": "FORBIDDEN",
        "container_toolkit": "REQUIRED_IF_GPU_CONTAINER" if probe.get("container_runtime") else "NOT_REQUIRED",
        "tensorrt": "OPTIONAL_AFTER_BENCHMARK",
        "triton": "OPTIONAL_ONLY_FOR_PROVEN_MULTI_MODEL_CONCURRENCY",
        "nvenc_nvdec": "OPTIONAL_AFTER_FFMPEG_BENCHMARK",
        "nsight": "DEVELOPMENT_ONLY",
        "llm_inference": "USER_DEVICE_ONLY_SERVER_GPU_FORBIDDEN",
        "tensorrt_llm": "FORBIDDEN_ON_SERVER",
        "cloud_fallback": "BLOCK",
    }
