"""Make the CUDA and cuDNN libraries loadable by ONNX Runtime on Windows, without breaking PyTorch."""
from __future__ import annotations

import ctypes
import glob
import os
import sys
import sysconfig

# Load order matters: each library depends on the ones before it.
CUDA_LIBRARIES = ('cudart64_*.dll', 'cublasLt64_*.dll', 'cublas64_*.dll', 'cufft64_*.dll', 'curand64_*.dll')
CUDNN_LIBRARY = 'cudnn64_9.dll'

_loaded: list[str] | None = None


def load_nvidia_libraries() -> list[str]:
    """
    Load CUDA 12 and cuDNN 9 so the face models (ONNX Runtime) can use the graphics card.

    Two things make this necessary. ONNX Runtime's own loader does not find the `nvidia-*` pip
    packages in every install layout. And PyTorch ships its own CUDA libraries: if a different
    copy of one of them is loaded first, PyTorch fails to import. So when PyTorch is installed
    its CUDA libraries are the ones loaded here, and only cuDNN 9, which PyTorch does not ship,
    comes from the `nvidia-cudnn` package. This must run before PyTorch is imported.

    Returns the names loaded. An empty list means a CPU-only setup, which is fine.
    """
    global _loaded
    if _loaded is not None:
        return _loaded
    _loaded = []
    if sys.platform != 'win32':
        return _loaded

    packages = sysconfig.get_paths()['purelib']
    cudnn_folder = os.path.join(packages, 'nvidia', 'cudnn', 'bin')
    if not os.path.isfile(os.path.join(cudnn_folder, CUDNN_LIBRARY)):
        return _loaded

    torch_folder = os.path.join(packages, 'torch', 'lib')
    if glob.glob(os.path.join(torch_folder, 'cudart64_*.dll')):
        cuda_folders = [torch_folder]
    else:
        cuda_folders = sorted(glob.glob(os.path.join(packages, 'nvidia', '*', 'bin')))

    folders = cuda_folders + [cudnn_folder]
    for folder in folders:
        os.add_dll_directory(folder)
    # The CUDA provider library is found through PATH, not through add_dll_directory.
    os.environ['PATH'] = os.pathsep.join(folders) + os.pathsep + os.environ.get('PATH', '')

    paths = [path for pattern in CUDA_LIBRARIES for folder in cuda_folders for path in glob.glob(os.path.join(folder, pattern))]
    paths.append(os.path.join(cudnn_folder, CUDNN_LIBRARY))
    for path in paths:
        try:
            ctypes.WinDLL(path)
            _loaded.append(os.path.basename(path))
        except OSError:
            pass  # a missing piece means the CPU provider is used instead
    return _loaded
