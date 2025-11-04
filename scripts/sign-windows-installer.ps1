# Self-sign Windows installer (Development only)
# This will still show warnings but allows testing

param(
    [string]$InstallerPath = ".\ui\dist\automagik-omni-ui-1.0.0-setup.exe"
)

Write-Host "Creating self-signed certificate..." -ForegroundColor Cyan

# Create self-signed certificate
$cert = New-SelfSignedCertificate `
    -Type CodeSigningCert `
    -Subject "CN=Automagik Omni Development" `
    -CertStoreLocation "Cert:\CurrentUser\My" `
    -NotAfter (Get-Date).AddYears(1)

Write-Host "Certificate created: $($cert.Thumbprint)" -ForegroundColor Green

# Export certificate (optional - for distribution)
$certPath = "automagik-omni-dev-cert.pfx"
$password = ConvertTo-SecureString -String "dev-password-123" -Force -AsPlainText
Export-PfxCertificate -Cert $cert -FilePath $certPath -Password $password

Write-Host "Signing installer..." -ForegroundColor Cyan

# Sign the installer
Set-AuthenticodeSignature -FilePath $InstallerPath -Certificate $cert -TimestampServer "http://timestamp.digicert.com"

Write-Host "✓ Installer signed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Note: Self-signed certificates still show SmartScreen warnings." -ForegroundColor Yellow
Write-Host "For production, use a certificate from a trusted CA (DigiCert, Sectigo, etc.)" -ForegroundColor Yellow
