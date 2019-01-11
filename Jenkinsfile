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
            echo sh(returnStdout: true, script: 'env')
        }

        stage("Run Tests") {
            sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} ${img_tag} python3 setup.py covxml"
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
                stackformation.masterDockerHub()
            }
        }

        if (env.TAG_NAME) {
            stage("Publish To PyPi") {

                stackformation.publishPypi(env.WORKSPACE, img_tag)

            }
            stage("Push Tag to DockerHub") {
                withCredentials([usernamePassword(credentialsId: '***REMOVED***', passwordVariable: 'PW', usernameVariable: 'UN')]) {
                    //sleep to allow pypi to register the new version so we can install
                    echo "Sleeping for pypi to register latest tag"
                    sleep(60)
                    //echo "Building tagged container image"
                    //// Build Latest Tag
                    //sh "docker build -f Dockerfile-tagged -t ibejohn818/stackformation:${env.TAG_NAME} ."
                    //echo "Push to docker hub Tagged"
                    //sh "docker login --username ${env.UN} --password ${env.PW}"
                    //sh "docker push ibejohn818/stackformation:${env.TAG_NAME}"
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
