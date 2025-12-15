import logging
import os
from datetime import datetime

class LogHelper:
    _instances = {}

    def __new__(cls, log_name='default', base_log_dir='logs', log_level=logging.INFO):
        if log_name not in cls._instances:
            cls._instances[log_name] = super(LogHelper, cls).__new__(cls)
            cls._instances[log_name].__init_instance(log_name, base_log_dir, log_level)
        return cls._instances[log_name]

    def __init_instance(self, log_name, base_log_dir, log_level):
        self._log_name = log_name
        self.base_log_dir = base_log_dir
        self.log_level = log_level
        self.logger = logging.getLogger(self._log_name)
        self.logger.setLevel(log_level)

        self.setup_log_directory()
        self.setup_handlers()

        self._initialized = True

    def setup_log_directory(self):
        # 获取当前日期
        today = datetime.today()
        year = today.strftime('%Y')
        month = today.strftime('%m')
        day = today.strftime('%Y%m%d')

        # 构建目录结构
        self.log_dir = os.path.join(self.base_log_dir, year, month)
        os.makedirs(self.log_dir, exist_ok=True)

        # 日志文件名称
        self.log_file = os.path.join(self.log_dir, f'{day}.log')

    def setup_handlers(self):
        if not self.logger.handlers:
            # 创建处理器
            console_handler = logging.StreamHandler()
            file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
            console_handler.setLevel(self.log_level)
            file_handler.setLevel(self.log_level)

            # 创建格式器并添加到处理器
            console_format = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
            file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            console_handler.setFormatter(console_format)
            file_handler.setFormatter(file_format)

            # 添加处理器到记录器
            self.logger.addHandler(console_handler)
            self.logger.addHandler(file_handler)

    @staticmethod
    def get_logger(log_name='default'):
        if log_name in LogHelper._instances:
            return LogHelper._instances[log_name].logger
        else:
            return LogHelper(log_name).logger

    def debug(self, message):
        self.logger.debug(message)
        print(message)

    def info(self, message):
        self.logger.info(message)
        print(message)

    def warning(self, message):
        self.logger.warning(message)
        print(message)

    def error(self, message):
        self.logger.error(message)
        print(message)

    def critical(self, message):
        self.logger.critical(message)
        print(message)

