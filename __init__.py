#!/usr/bin/env python2
from main import mainApp

def load_config(config):
    mainApp(config).run()

if __name__ == '__main__':
    mainApp().run()