#!/usr/bin/env groovy

import hudson.model.*
import hudson.EnvVars


node {

    try {

        //def img_tag = "${env.BRANCH_NAME.toLowerCase()}${env.BUILD_ID}"
        def img_tag =  "stackformationjenkins"
        // load shared jenkins code
        @Library('shared-pipelines')_

        stage("Stage Repo") {
            echo "Checkout repo"
            checkout scm
        }

        stage("Build Test Image") {
            sh "docker build -f Dockerfile-test -t ${img_tag} ."
        }

        stage("Run Tests") {
            sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} -v /etc/passwd:/etc/passwd:ro -ujhardy ${img_tag} python3 setup.py covxml"
            sh "chmod -R 777 ${env.WORKSPACE}"
            currentBuild.result = "SUCCESS"
        }

        stage("Send Code Coverage") {
            if (currentBuild.result == "SUCCESS") {
                stackformation.coverage()
            } else {
                echo "Skipping coverage report..."
            }
        }

        if (env.BRANCH_NAME == "master") {
            stage("Push latest to DockerHub") {
                if (currentBuild.result == "SUCCESS") {
                    stackformation.masterDockerHub()
                } else {
                    echo "Skipping push to DockerHub"
                }
            }
        }

        if (env.TAG_NAME) {
            stage("Publish To PyPi") {
                stackformation.publishPypi(env.WORKSPACE, img_tag)
            }
            stage("Push Tag to DockerHub") {
                stackformation.tagDockerHub()
            }
        }

    } catch(Exception err) {
        currentBuild.result = "FAILURE"
    } finally {

        //def img_tag = "${env.BRANCH_NAME.toLowerCase()}${env.BUILD_ID}"
        //sh "docker rmi ${img_tag} --force"
    }
}
