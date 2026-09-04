<#
.SYNOPSIS
    Randomly sample 3,000 images directly out of the seafloor_sediments zip
    archive into seafloor_sediments_sample\, without extracting the other
    ~400k images to disk.

.NOTES
    This exists because Python's zipfile module chokes on this archive's
    Zip64 metadata (BadZipFile: zipfiles that span multiple disks / Bad
    magic number for central directory). .NET's System.IO.Compression is a
    completely different implementation and reads this file fine.

    After a successful sample, the original zip is deleted to free disk
    space (confirmed by the user) -- only the 3,000-image sample folder is
    kept.

.USAGE
    powershell -ExecutionPolicy Bypass -File scripts\sample_negatives.ps1
    (or just: .\scripts\sample_negatives.ps1  from inside the echoedvoidai folder)
#>

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

# --- config -----------------------------------------------------------
$repoRoot  = Split-Path -Parent $PSScriptRoot
$rawDir    = Join-Path $repoRoot "data\raw\seafloor_sediments"
$zipPath   = Join-Path $rawDir "sss_ssl_dataset_N713_384.zip"
$outDir    = Join-Path $rawDir "seafloor_sediments_sample"
$nSample   = 3000
$imageExts = @(".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
$seed      = 42
$deleteZipAfter = $true   # user confirmed: remove the 9.3GB zip once the sample is verified
# ------------------------------------------------------------------------

if (-not (Test-Path -LiteralPath $zipPath)) {
    Write-Error "Zip not found: $zipPath"
    exit 1
}

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

Write-Host "Opening zip with .NET's zip reader (this can take a bit for a 9GB archive)..."
try {
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
} catch {
    Write-Error "Could not open the zip with .NET either: $($_.Exception.Message)"
    Write-Error "The archive may be genuinely corrupted/truncated. Try re-downloading it, or run '7z t `"$zipPath`"' (if you have 7-Zip) to check its integrity."
    exit 1
}

$take = 0
try {
    $imageEntries = @($archive.Entries | Where-Object {
        $_.Name -ne "" -and ($imageExts -contains [System.IO.Path]::GetExtension($_.FullName).ToLower())
    })
    Write-Host "Found $($imageEntries.Count) images inside $(Split-Path $zipPath -Leaf)"

    if ($imageEntries.Count -lt $nSample) {
        Write-Host "WARNING: only $($imageEntries.Count) images available, sampling all of them"
    }

    $take = [Math]::Min($nSample, $imageEntries.Count)

    # seeded Fisher-Yates partial shuffle -> first $take elements are our sample
    $rand = New-Object System.Random($seed)
    $arr = $imageEntries
    $n = $arr.Count
    for ($i = 0; $i -lt $take; $i++) {
        $j = $i + $rand.Next($n - $i)
        $tmp = $arr[$i]; $arr[$i] = $arr[$j]; $arr[$j] = $tmp
    }
    $sample = $arr[0..([Math]::Max($take - 1, 0))]

    $count = 0
    foreach ($entry in $sample) {
        $fileName = [System.IO.Path]::GetFileName($entry.FullName)
        $destPath = Join-Path $outDir $fileName
        if (Test-Path -LiteralPath $destPath) {
            $stem = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
            $ext  = [System.IO.Path]::GetExtension($fileName)
            $destPath = Join-Path $outDir "${stem}_$count$ext"
        }
        [System.IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destPath, $true)
        $count++
        if (($count % 250) -eq 0 -or $count -eq $take) {
            Write-Host "  copied $count/$take"
        }
    }

    Write-Host "Done. $count images written to $outDir"
} finally {
    $archive.Dispose()
}

$actualCount = (Get-ChildItem -LiteralPath $outDir -File).Count
if ($actualCount -lt $take) {
    Write-Host "Sample looks incomplete ($actualCount/$take) -- leaving the zip in place, please check manually."
    exit 1
}

if ($deleteZipAfter) {
    $sizeGB = [Math]::Round((Get-Item -LiteralPath $zipPath).Length / 1GB, 1)
    Write-Host "Removing source zip ($sizeGB GB): $zipPath"
    try {
        Remove-Item -LiteralPath $zipPath -Force -ErrorAction Stop
        Write-Host "Zip deleted. Only seafloor_sediments_sample\ remains in this folder."
    } catch {
        Write-Warning "Sample is complete, but deleting the zip failed: $($_.Exception.Message)"
        Write-Warning "You can delete it by hand once nothing else has it open: $zipPath"
    }
}
