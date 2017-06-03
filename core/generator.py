#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    The main function of this module is :
    use /resources/template/dc-compose.yml and devices info to generate some docker-compose.yml
    @author Juan Liu
    @date 2017/03/01
    @modifier
"""

import logging
import os
import subprocess
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader
from stf_selector.selector import where
import my_thread
from conftest import docker_composes_data, get_stf_devices, get_test_users
from config import LOCAL_LOG_DIR
from log import LOGGER

LOGGER.info("*********Begin******")
logger = logging.getLogger(__name__)
base_res_path = os.path.join(os.pardir, "resources")  # resources file path
template_path = os.path.join(base_res_path, "template")  # template file path
docker_composes_files_path = os.path.join(base_res_path, "dockercomposes")  # docker-compse.yml file path
package_name = "core"


def generator_docker_composes(template_path,
                              docker_compose_template_name,
                              app_template_name,
                              docker_composes_files_path,
                              data):
    """
    Use docker_compose.yml template and app_template.sh template to
    generate docker_compose.yml and app_template.sh files

    :param template_path: template path
    :param docker_compose_template_name: docker_compose.yml template name
    :param app_template_name: app.sh template name
    :param docker_composes_files_path: where to put docker_compose.yml
    :param data: docker_compose data
    :return: generate some docker_compose.yml and app.sh under docker composes
    """
    logger.info("Begin to generate docker-compose.yml files.")
    if data is None or len(data) == 0:
        logging.info("No devices to generate docker-compose-files")
        return
    env = Environment(loader=FileSystemLoader(template_path))
    docker_compose_template = env.get_template(docker_compose_template_name)
    app_template = env.get_template(app_template_name)
    for docker_compose_data in data:
        app_data = defaultdict(list)
        app_data['APK_NAME'] = docker_compose_data['APK_NAME']
        app_data['DEVICES_NAME'] = docker_compose_data['DEVICES_NAME']
        app_data['CASE_NAME'] = docker_compose_data['CASE_NAME']
        serial = docker_compose_data['SERIAL']
        docker_compose_data['DOCKER_COMPOSE_VOLUMES'] = docker_compose_data['DOCKER_COMPOSE_VOLUMES'] + \
                                                        serial + ":/app_shell"
        docker_compose_data['CONTAINER_NAME'] = serial
        logs_volumes = docker_compose_data['APPIUM_CARTIEREJ_LOGS_VOLUMES']
        docker_compose_data['APPIUM_CARTIEREJ_LOGS_VOLUMES'] = str(logs_volumes).replace("RANDOM", serial)
        app_res = app_template.render(app_data)
        docker_compose_res = docker_compose_template.render(docker_compose_data)

        devices_path = os.path.join(docker_composes_files_path, serial)
        if not os.path.exists(devices_path):
            os.mkdir(devices_path)
        dc_temp = os.path.join(devices_path, "docker-compose.yml")
        app_temp = os.path.join(devices_path, "app.sh")

        with open(dc_temp, "w") as f1:
            f1.write(docker_compose_res)
        with open(app_temp, "w") as f2:
            f2.write(app_res)

    logger.info("Created " + str(len(data)) + " docker-compose.yml.")


def up_docker_composes(docker_composes_yml_base_path=None):
    """
    Use docker compose tool to up all docker_compose.yml under dockercomposes file
    :param docker_composes_yml_base_path: docker compose files path
    :return:
    """
    logger.info("Use 'docker-compose up' to start all docker-compose.yml")
    q = my_thread.put_jobs(docker_composes_yml_base_path)
    # my_thread.MyThread(q).start()
    threads = []
    for i in range(my_thread.NUM_WORKERS):
        try:
            t = my_thread.MyThread(q)
            t.start()
            t.setDaemon(True)
            threads.append(t)
        except Exception as err:
            logger.error(err)

    for x in threads:
        x.join()


def rm_docker_container():
    """
    Remove containers which generated by docker-compose up.

    :return:
    """
    logger.info("Docker rm cache container")
    try:
        subprocess.call(["docker-compose down"], shell=True)
    except Exception as err:
        logger.error(err)
    finally:
        logger.info("release containers.")


def delete_docker_composes(docker_composes_files_path=None):
    """
    Delete all docker_compose.yml files under docker composes file
    :param docker_composes_files_path: where docker_compose.yml put
    :return:
    """
    logger.info("Delete docker_compose yaml files under directory.")
    if docker_composes_files_path is not None:
        for docker_composes in os.listdir(docker_composes_files_path):
            docker_composes = os.path.join(docker_composes_files_path, docker_composes)
            if os.path.isdir(docker_composes):
                subprocess.call(["rm", "-rf", docker_composes])
            else:
                subprocess.call(["rm", "-f", docker_composes])
    else:
        logger.info("Docker_composes_files_path is not exists.")


def delete_log_files(log_dir=None):
    """
    Delete logs
    :param log_dir: where logs exists
    :return:
    """
    delete_docker_composes(log_dir)


if __name__ == '__main__':
    logger = logging.getLogger(" ")
    delete_docker_composes(docker_composes_files_path)
    delete_log_files(LOCAL_LOG_DIR)
    # filter conditions
    cond = (where("present").exists()) \
           & (where("abi").exists()) \
           & (where("using").exists()) \
           & (where('present') == True) \
           & (where('using') == False)
    devices = get_stf_devices(cond=cond)
    # read users
    test_users_file = os.path.join(base_res_path, "test_users.txt")
    users = get_test_users(test_user_file=test_users_file, size=len(devices))
    # generate docker_composes_data
    data = docker_composes_data(users=users, devices=devices)
    generator_docker_composes(template_path,
                              "docker_compose_template.yml",
                              "app_template.sh",
                              docker_composes_files_path,
                              data)
    # up docker compose
    up_docker_composes(docker_composes_files_path)

