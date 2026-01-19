terraform {
  required_providers {
    local = {
        source = "hashicorp/local"
        version = "~> 2.4.0"
    }
  }
}

provider "local" {}

resource "local_file" "spotify-event-pipeline" {
  content = "hello world, this file was created with terraform"
  filename = "${path.module}/spotify-event-pipeline.txt"
}

