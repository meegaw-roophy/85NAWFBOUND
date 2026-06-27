param(
    [string]$Port = "8000"
)

Write-Host "Forwarding Stripe events to localhost:$Port/api/v1/webhooks/stripe"
stripe listen --forward-to "localhost:$Port/api/v1/webhooks/stripe"
