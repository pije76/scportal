from configobj import ConfigObj


class ForecastConfiguration:
    def __init__(self, config_path):
        configuration = ConfigObj(config_path)

        self.validate_config(configuration)

        self.configuration = configuration

    def validate_config(self, configuration):
        if "url" not in configuration or "api_key" not in configuration:
            raise Exception("url or key not found in configuration file")
