def test_package_imports():
    import importlib

    importlib.import_module("backend.core")
    importlib.import_module("backend.providers")
    importlib.import_module("backend.utils")
