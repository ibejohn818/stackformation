#!/usr/bin/env groovy

import hudson.model.*
import hudson.EnvVars


node {

    try {

        def img_tag = "${env.BRANCH_NAME.toLowerCase()}${env.BUILD_ID}"
        def pwd = pwd()

        stage("Stage Repo") {
            echo "Checkout repo"
            checkout scm
        }

        stage("Build Test Image") {
            sh "docker build -f Dockerfile-test -t ${img_tag} ."
        }

        stage("Run Tests") {
            sh "docker run --rm -v ${pwd}:${pwd} -w ${pwd} ${img_tag} python3 setup.py covxml"
            currentBuild.status = "SUCCESS"
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

    } catch(Exception err) {
        currentBuild.result = "FAILURE"
    } finally {

        def img_tag = "${env.BRANCH_NAME.toLowerCase()}${env.BUILD_ID}"
        sh "docker rmi ${img_tag} --force"
    }
}
