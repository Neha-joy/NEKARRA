Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM | Format-Table -AutoSize
Write-Host 'For NVIDIA CUDA details (if installed):'
nvidia-smi
