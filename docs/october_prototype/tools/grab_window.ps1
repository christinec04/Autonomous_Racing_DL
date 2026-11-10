# Saves the Webots main window to the given png, then closes Webots.
param([string]$Out)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
public struct RECT { public int L, T, R, B; } }
"@
[W]::SetProcessDPIAware() | Out-Null
$p = Get-Process webots-bin -ErrorAction SilentlyContinue | Select-Object -First 1
if ($p) {
  $r = New-Object W+RECT
  [W]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null
  $bmp = New-Object System.Drawing.Bitmap ($r.R - $r.L), ($r.B - $r.T)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $dc = $g.GetHdc()
  [W]::PrintWindow($p.MainWindowHandle, $dc, 2) | Out-Null
  $g.ReleaseHdc($dc)
  $bmp.Save($Out)
  Stop-Process -Id $p.Id -Force
}
Get-Process webots -ErrorAction SilentlyContinue | Stop-Process -Force
