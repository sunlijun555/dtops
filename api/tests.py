
import paramiko
import re
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger()


class SSH:

    def __init__(self, host, port, username, password, su_password=None):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._su_password = su_password

        self._ssh_client = None
        self._invoke_shell = None

    def connect(self, connect_invoke_shell=False):
        try:
            self._ssh_client = paramiko.SSHClient()
            self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self._ssh_client.connect(hostname=self._host, port=self._port, username=self._username, password=self._password)
            if connect_invoke_shell:
                self._invoke_shell = self._ssh_client.invoke_shell()
                time.sleep(2)
                self._invoke_shell.recv(1024).decode()
        except Exception as error:
            logger.error(f"连接服务器出错: {error}")

    def exec_invoke_shell_command(self, command, end="Euler:"):
        """
        执行invoke_shell的命令，一发一收
        @param command: 命令
        @param end: 命令结束符
        @return: 命令返回结果
        """
        self._invoke_shell.send(f"{command}\n")
        time.sleep(1)
        while True:
            part = self._invoke_shell.recv(1024).decode()
            print(f"接收数据: {part}")
            if end in part:
                break
            # 处理yes/no
        return part

    def exec_client_command(self, command):
        stdin, stdout, stderr = self._ssh_client.exec_command(command)
        return stdout.read().decode()

    def switch_root_user(self):
        assert self._invoke_shell is not None
        self.exec_invoke_shell_command("su", "Password")
        self.exec_invoke_shell_command(f"{self._su_password}")

    def close(self):
        self._ssh_client.close()
        if hasattr(self._invoke_shell, 'close'):
            self._invoke_shell.close()


class ITS800Collector:

    def __init__(self,
                 save_dir="/home/broadxt/data4t/share/sunlijun/its800",
                 its800_data_dir="/opt/third_algorithm_D/debug_its_period/debug",
                 thread_nums=10):

        self._save_dir = save_dir
        self._its800_data_dir = its800_data_dir
        self._thread_nums = thread_nums
        self._include_dirs = ["arrivalInfo", "conf", "det", "fusionRaw", "monitor", "radar",
                              "sectionConnMsg", "sync", "videoInfo", "attri", "coredump",
                              "fusion", "metric", "output", "sectionConn", "snap", "track"]

        # 目标服务器ssh定义
        self._target_ssh = None
        self._target_ip = None
        self._target_port = None
        self._target_username = None
        self._target_password = None

    def set_target_ssh(self, ip=None, port=None, username=None, password=None):
        self._target_ip = ip
        self._target_port = port
        self._target_username = username
        self._target_password = password
        target_ssh = SSH(ip, port, username, password)
        target_ssh.connect()
        self._target_ssh = target_ssh

    def exec_job(self, its800_host_config, compress):
        data_pattern_obj = re.compile(r"\d+-\d+-\d+-\d+-\d+-\d+")
        project = its800_host_config.get('project')
        ip = its800_host_config.get('ip')
        port = its800_host_config.get('port')
        username = its800_host_config.get('username')
        password = its800_host_config.get('password')
        su_password = its800_host_config.get('su_password')
        ssh = SSH(ip, port, username, password, su_password)
        ssh.connect(connect_invoke_shell=True)
        ssh.switch_root_user()
        result = ssh.exec_invoke_shell_command(f"ls {self._its800_data_dir} --color=no")
        if not result:
            logger.error(f"its800收集数据目录为空，请检查")
        data = data_pattern_obj.findall(result)
        base_dir = f"{self._save_dir}/{project}/{ip}"

        day_pattern_obj = re.compile(r'\d+-\d+-\d+')
        for file_name in data[:2]:
            day_match = day_pattern_obj.match(file_name)
            if not day_match:
                continue
            day_str = day_match.group()
            target_host_file = f"{base_dir}/{day_str}/{file_name}"
            if compress:
                target_host_file_status = self._target_ssh.exec_client_command(
                    f"[ -f {target_host_file}.tar.gz ] && echo 1")
            else:
                target_host_file_status = self._target_ssh.exec_client_command(f"[ -d {target_host_file} ] && echo 1")
            if "1" in target_host_file_status:
                continue
            self._target_ssh.exec_client_command(f"mkdir -p {target_host_file}")
            its800_host_file = f"{self._its800_data_dir}/{file_name}"
            include_files = ",".join(self._include_dirs)
            sub_files_path = "%s/{%s}" % (its800_host_file, include_files)
            scp_cmd = f"scp -o StrictHostKeyChecking=no -r -P {self._target_port} {sub_files_path}" \
                      f" {self._target_username}@{self._target_ip}:{target_host_file}"

            ssh.exec_invoke_shell_command(scp_cmd, end="password:")
            ssh.exec_invoke_shell_command(self._target_password)
            if compress:
                self._target_ssh.exec_client_command(f"cd {base_dir}/{day_str};tar -czf {file_name}.tar.gz {file_name}")
                self._target_ssh.exec_client_command(f"rm -rf {target_host_file}")
        ssh.close()

    def collector(self, target_host_config, its800_hosts_config, compress=True):
        """
        收集多个its800数据到指定服务器
        @param target_host_config: 目标服务器配置
        @param its800_hosts_config: 多个its800配置
        @param compress: 是否压缩数据
        @return:
        """
        # 配置目标服务器
        self.set_target_ssh(**target_host_config)
        # 配置its800服务器配置列表，遍历，过滤视频数据，在目标服务器创建project/ip/node_id/file_name 目录，拉取数据到此目录
        future_result = []
        with ThreadPoolExecutor(self._thread_nums) as executor:
            for its800_host_config in its800_hosts_config:
                # lambda表达式用于submit传递多个参数
                future_result.append(executor.submit(lambda p: self.exec_job(*p), (its800_host_config, compress)))
        for future_obj in as_completed(future_result):
            future_obj.result()
        self._target_ssh.close()


if __name__ == '__main__':

    its800_collector = ITS800Collector()

    target_host = {
        "ip": "172.16.7.60",
        "port": 22,
        "username": "broadxt",
        "password": "broadxt333",
    }
    its800_hosts = [
        {
            "project": "jichang_hiway",
            "ip": "10.10.40.249",
            "port": 22,
            "username": "admin",
            "password": "jichang@333",
            "su_password": "broadxt12#$"
        },
        {
            "project": "jichang_hiway",
            "ip": "10.10.40.248",
            "port": 22,
            "username": "admin",
            "password": "jichang@333",
            "su_password": "broadxt12#$"
        }
    ]
    # target_host, its800_hosts = args
    its800_collector.collector(target_host, its800_hosts, compress=True)
    # its_ip = '10.10.40.249'
    # its_port = 22
    # its_username = 'admin'
    # its_password = 'jichang@333'
    # its_su_password = 'broadxt12#$'
    #
    # target_password = "broadxt333"
    #
    # ssh = SSH(its_ip, its_port, its_username, its_password, its_su_password)
    #
    # ssh.connect(connect_invoke_shell=True)
    # ssh.switch_root_user()
    # source_dir = r'/opt/third_algorithm_D/debug_its_period/debug/2022-06-11-0-0-10/{radar,track,fusion}'
    # target_dir = '/home/broadxt/data4t/share/sunlijun/2022-06-11-0-0-10'
    # scp_cmd = f'scp -r {source_dir} broadxt@172.16.7.60:{target_dir} '
    #
    # # print(ssh.exec_invoke_shell_command("ls /opt/third_algorithm_D/debug_its_period/debug --color=no"))
    #
    # ssh.exec_invoke_shell_command(scp_cmd, end="password:")
    # ssh.exec_invoke_shell_command(target_password)
    # ssh.close()

    # target_ip = "172.16.7.60"
    # target_port = 22
    # target_username = "broadxt"
    # target_password = "broadxt333"
    # target_ssh = SSH(target_ip, target_port, target_username, target_password)
    # target_ssh.connect()
    # print(target_ssh.exec_client_command("[ -d /home ] && echo 1"))
    # target_ssh.close()
