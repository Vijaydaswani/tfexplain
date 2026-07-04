terraform {
  required_version = ">= 1.6.0"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
  }
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

data "cloudflare_zone" "main" {
  name = var.zone_name
}

resource "cloudflare_record" "app" {
  zone_id = data.cloudflare_zone.main.id
  name    = var.record_name
  value   = var.record_value
  type    = "CNAME"
  proxied = true
}

resource "cloudflare_ruleset" "cache" {
  zone_id = data.cloudflare_zone.main.id
  name    = "cache-static"
  kind    = "zone"
  phase   = "http_request_cache_settings"
}
