#!/usr/bin/env groovy

import hudson.model.*
import hudson.EnvVars


node {

    try {

        //def img_tag = "${env.BRANCH_NAME.toLowerCase()}${env.BUILD_ID}"
        def img_tag =  "stackformationjenkins"
        stage("Stage Repo") {
            echo "Checkout repo"
            checkout scm
        }

        stage("Build Test Image") {
            sh "docker build -f Dockerfile-test -t ${img_tag} ."
            echo sh(returnStdout: true, script: 'env')
        }

        stage("Run Tests") {
            sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} ${img_tag} python3 setup.py covxml"
            currentBuild.result = "SUCCESS"
        }

        stage("Send Code Coverage") {
            if (currentBuild.result == "SUCCESS") {
                echo "Sending Coverage Report..."
                withCredentials([[$class: 'StringBinding', credentialsId: 'StackformationCodecov', variable: 'CODECOV']]) {
                    echo "KEY: ${env.CODECOV}"
                    sh "curl -s https://codecov.io/bash | bash -s - -t ${env.CODECOV}"
                }
            } else {
                echo "Skipping coverage report..."
            }
        }

        if (env.BRANCH_NAME == "master") {
            stage("Trigger Docker Latest Build") {
                withCredentials([string(credentialsId: 'StackformationDockerHubBuildToken', variable: 'BUILD_TOKEN')]) {
                    sh "curl -H 'Content-Type: application/json' --data '{\"source_type\": \"Branch\", \"source_name\": \"master\"}' -X POST https://registry.hub.docker.com/u/ibejohn818/stackformation/trigger/${env.BUILD_TOKEN}/"
                }
            }
        }

        if (env.BRANCH_NAME == "dockerhub-jenkins-push") {
            stage("Push latest to DockerHub") {
                withCredentials([usernamePassword(credentialsId: 'ibejohn818Dockerhub', passwordVariable: 'PW', usernameVariable: 'UN')]) {
                    // Build Latest Tag
                    sh "docker build -t ibejohn818/stackformation:latest ."
                    echo "Push to docker hub"
                    sh "docker login --login ${env.UN} --password ${env.PW}"
                    sh "docker push ibejohn818/stackformation:latest"
                }
            }
        }

        if (env.TAG_NAME) {
            stage("Publish To PyPi") {

                echo "Cleaning"
                sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} ${img_tag} make clean"
                echo "Build DIST Package"
                sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} ${img_tag} python3 setup.py sdist"

                withCredentials([usernamePassword(credentialsId: 'ibejohn818PyPi', passwordVariable: 'PYPIPASSWD', usernameVariable: 'PYPIUSER')]) {
                    echo "Send to PyPi"

                    def dist_name = "jh-stackformation-${env.TAG_NAME}.tar.gz"

                    sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} ${img_tag} twine upload dist/${dist_name} -u ${env.PYPIUSER} -p ${env.PYPIPASSWD}"
                }

            }
            stage("Trigger Docker Hub Build") {
                withCredentials([string(credentialsId: 'StackformationDockerHubBuildToken', variable: 'BUILD_TOKEN')]) {
                    sh "curl -H 'Content-Type: application/json' --data '{\"source_type\": \"Tag\", \"source_name\": \"${env.TAG_NAME}\"}' -X POST https://registry.hub.docker.com/u/ibejohn818/stackformation/trigger/${env.BUILD_TOKEN}/"
                }
            }
        }

    } catch(Exception err) {
        currentBuild.result = "FAILURE"
    } finally {

        //def img_tag = "${env.BRANCH_NAME.toLowerCase()}${env.BUILD_ID}"
        //sh "docker rmi ${img_tag} --force"
    }
}
