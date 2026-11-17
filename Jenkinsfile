pipeline {
    agent any

    triggers {
        pollSCM('H/5 * * * *')
        cron('H H * * *')
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    stages {
        stage('Install dependencies') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 -m pip install -r requirements.txt'
                    } else {
                        bat 'python -m pip install -r requirements.txt'
                    }
                }
            }
        }

        stage('Test') {
            steps {
                script {
                    if (isUnix()) {
                        sh 'python3 -m unittest discover -s tests -v'
                    } else {
                        bat 'python -m unittest discover -s tests -v'
                    }
                }
            }
        }
    }

    post {
        always {
            echo "Library Desk pipeline finished: ${currentBuild.currentResult}"
        }
    }
}
