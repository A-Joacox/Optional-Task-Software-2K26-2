# Ejecuta SonarScanner CLI en Docker contra el SonarQube de compose.yaml.
# Requisitos: `docker compose up -d` en marcha y coverage.xml generado con pytest.
$root = Split-Path $PSScriptRoot -Parent
$container = docker compose -f "$root\compose.yaml" ps -q sonarqube
$network = docker inspect $container --format '{{range $name, $_ := .NetworkSettings.Networks}}{{$name}}{{end}}'

$secret = Read-Host "Token de SonarQube" -AsSecureString
$env:SONAR_TOKEN = [System.Net.NetworkCredential]::new("", $secret).Password
try {
    docker run --rm --network $network `
        -e SONAR_HOST_URL=http://sonarqube:9000 -e SONAR_TOKEN `
        -v "${root}:/usr/src" `
        sonarsource/sonar-scanner-cli:latest
} finally {
    Remove-Item Env:SONAR_TOKEN
}
