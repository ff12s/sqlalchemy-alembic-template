# Compare PostgreSQL schemas: main, dev
# Requires: Docker, DBs reachable from the pgquarrel container.
# Connection params are read from env (PGHOST/PGPORT/PGUSER/PGPASSWORD) with local-dev defaults.

$HostAddr = if ($env:PGHOST) { $env:PGHOST } else { "host.docker.internal" }
$Port = if ($env:PGPORT) { $env:PGPORT } else { "5432" }
$User = if ($env:PGUSER) { $env:PGUSER } else { "postgres" }
$Password = if ($env:PGPASSWORD) { $env:PGPASSWORD } else { "postgres" }
# source = эталон, target = что приводим к эталону
# SQL применяется к target, чтобы он стал как source
# main -> dev:   применяем к dev, чтобы стал как main
$Pairs = @(
    @("main", "dev")
)

New-Item -ItemType Directory -Force -Path reports | Out-Null

Write-Host "Building pgquarrel image..." -ForegroundColor Cyan
docker build -t pgquarrel .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed" -ForegroundColor Red
    exit 1
}

$dockerRunArgs = @(
    "run", "--rm",
    "-v", "${PWD}/reports:/reports",
    "-e", "PGPASSWORD=$Password"
)

foreach ($p in $Pairs) {
    $src, $tgt = $p[0], $p[1]
    $outFile = "${tgt}_to_${src}.sql"
    Write-Host "Migrating $tgt -> $src ..." -ForegroundColor Cyan

    $pgqArgs = @(
        "--source-host", $HostAddr, "--source-port", $Port, "--source-dbname", $src, "--source-username", $User,
        "--target-host", $HostAddr, "--target-port", $Port, "--target-dbname", $tgt, "--target-username", $User,
        "--source-no-password", "--target-no-password",
        "--ignore-version",
        "-f", "/reports/$outFile", "-s", "-t"
    )

    & docker @dockerRunArgs pgquarrel @pgqArgs

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  -> reports/$outFile" -ForegroundColor Green
    } else {
        Write-Host "  Error: $src vs $tgt" -ForegroundColor Red
    }
}

Write-Host "Done. Reports in reports/" -ForegroundColor Green
