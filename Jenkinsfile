#!/usr/bin/env groovy

import hudson.model.*
import hudson.EnvVars


node {

    try {

        stage("Stage Repo") {
            echo "Checkout repo"
            checkout scm
        }

        currentBuild.result = "FAILURE"

    } catch(Exception err) {
        currentBuild.result = "FAILURE"
    } finally {

    }
}
