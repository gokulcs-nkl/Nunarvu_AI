"""
Load the GPU libraries for the face models before anything else.

This package is imported first in every process (web server, camera worker, tests), which is
the only point that is reliably ahead of PyTorch. See `vision.gpu` for why the order matters.
On a computer without the NVIDIA libraries this does nothing.
"""
try:
    from vision.gpu import load_nvidia_libraries

    load_nvidia_libraries()
except Exception:  # never let an optional speed-up stop the application from starting
    pass
