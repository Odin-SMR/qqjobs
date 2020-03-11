node {
    checkout scm
    stage('Build') {
        sh "docker build -t docker2.molflow.com/devops/microq_admin ."
    }
    stage('Test') {
        sh "tox -- --runslow --runsystem"
    }
    stage("Push") {
        if (env.GIT_BRANCH == 'origin/master') {
            sh "docker push docker2.molflow.com/devops/microq_admin"
        }
    }
}
