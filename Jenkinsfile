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
                withCredentials([[$class: 'StringBinding', credentialsId: '***REMOVED***', variable: 'CODECOV']]) {
                    echo "KEY: ${env.CODECOV}"
                    sh "curl -s https://codecov.io/bash | bash -s - -t ${env.CODECOV}"
                }
            } else {
                echo "Skipping coverage report..."
            }
        }

        if (env.BRANCH_NAME == "master") {
            stage("Push latest to DockerHub") {
                withCredentials([usernamePassword(credentialsId: '***REMOVED***', passwordVariable: 'PW', usernameVariable: 'UN')]) {
                    // Build Latest Tag
                    sh "docker build -t ibejohn818/stackformation:master ."
                    echo "Push to docker hub"
                    sh "docker login --username ${env.UN} --password ${env.PW}"
                    sh "docker push ibejohn818/stackformation:master"
                }
            }
        }

        if (env.TAG_NAME) {
            stage("Publish To PyPi") {

                echo "Cleaning"
                sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} ${img_tag} make clean"
                echo "Build DIST Package"
                sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} ${img_tag} python3 setup.py sdist"

                withCredentials([usernamePassword(credentialsId: '***REMOVED***', passwordVariable: 'PYPIPASSWD', usernameVariable: 'PYPIUSER')]) {
                    echo "Send to PyPi"

                    def dist_name = "jh-stackformation-${env.TAG_NAME}.tar.gz"

                    sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} ${img_tag} twine upload dist/${dist_name} -u ${env.PYPIUSER} -p ${env.PYPIPASSWD}"
                }

            }
            stage("Push Tag to DockerHub") {
                withCredentials([usernamePassword(credentialsId: '***REMOVED***', passwordVariable: 'PW', usernameVariable: 'UN')]) {
                    // Build Latest Tag
                    sh "docker build -f Dockerfile-tagged -t ibejohn818/stackformation:${env.TAG_NAME} ."
                    echo "Push to docker hub Tagged"
                    sh "docker login --username ${env.UN} --password ${env.PW}"
                    sh "docker push ibejohn818/stackformation:${env.TAG_NAME}"
                    // Build the tagged and push as latest
                    sh "docker build -f Dockerfile-tagged -t ibejohn818/stackformation:latest ."
                    echo "Push to docker hub as latest"
                    sh "docker login --username ${env.UN} --password ${env.PW}"
                    sh "docker push ibejohn818/stackformation:latest"
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
