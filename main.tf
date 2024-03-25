# main.tf

provider "null" {}

resource "null_resource" "apply_flask_deployment" {
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = "kubectl apply -f ${path.module}/flask-deployment.yaml"
  }
}

resource "null_resource" "apply_flask_service" {
  triggers = {
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = "kubectl apply -f ${path.module}/flask-service.yaml"
  }
}
