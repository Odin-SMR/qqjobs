node {
    def qqjobsImage
    checkout scm
    stage('Build') {
        qqjobsImage = docker.build("odinsmr/microq_admin")
    }
    stage('Test') {
        sh "tox -r -- --runslow --runsystem"
    }
    if (env.BRANCH_NAME == 'master') {
      stage("Push") {
        withDockerRegistry([ credentialsId: "dockerhub-molflowbot", url: "" ]) {
          qqjobsImage.push(env.BUILD_TAG)
          qqjobsImage.push('latest')
      }
    }
  }
}
