pipeline {
    agent {
        label 'nomad-agent'
    }

    def img_tag =  "stackformationjenkins"

        stage("Stage Repo") {
            step("stage") {
                echo "Checkout repo"
                checkout scm
            }
        }

        stage("Build Test Image") {
            step("build") {
                sh "docker build -f Dockerfile-test -t ${img_tag} ."
            }
        }
        stage("Run Tests") {
            step("test") {
                sh "docker run --rm -v ${env.WORKSPACE}:${env.WORKSPACE} -w ${env.WORKSPACE} -v /etc/passwd:/etc/passwd:ro -ujhardy ${img_tag} python3 setup.py covxml"
                sh "chmod -R 777 ${env.WORKSPACE}"
                currentBuild.result = "SUCCESS"
            }
        }

        stage("Send Code Coverage") {
            step("coverage") {
                if (currentBuild.result == "SUCCESS") {
                    library 'shared-pipelines'
                    stackformation.coverage()
                } else {
                    echo "Skipping coverage report..."
                }
            }
        }

        if (env.BRANCH_NAME == "master") {
            stage("Push latest to DockerHub") {
                step("push dockerhub") {
                    if (currentBuild.result == "SUCCESS") {
                        library 'shared-pipelines'
                        stackformation.masterDockerHub()
                    } else {
                        echo "Skipping push to DockerHub"
                    }
                }
            }
        }

        if (env.TAG_NAME) {
            stage("Publish To PyPi") {
                step("pypi") {
                    library 'shared-pipelines'
                    stackformation.publishPypi(env.WORKSPACE, img_tag)
                }
            }
            stage("Push Tag to DockerHub") {
                step("task dockerhub") {
                    library 'shared-pipelines'
                    stackformation.tagDockerHub()
                }
            }
        }
}
