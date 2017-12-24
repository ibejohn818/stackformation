#!/usr/bin/env groovy

import hudson.model.*
import hudson.EnvVars


node {

    try {

        stage("Stage Repo") {
            echo "Checkout repo"
            checkout scm
        }


    } catch(Exception err) {
        currentBuild.result = "FAILURE"
    } finally {

    }
}
