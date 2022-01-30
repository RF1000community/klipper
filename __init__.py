def load_config(config):
    from .mainapp import MainApp
    kgui_object = MainApp(config)
    kgui_object.start()
    return kgui_object
