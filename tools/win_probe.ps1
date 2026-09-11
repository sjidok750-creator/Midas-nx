# CIVIL NX(CVLw) 최상위 창과 모달(#32770) 자식 텍스트 나열 — 스크린샷 대신 쓰는 200토큰짜리 모달 탐지기
$src = @'
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public class WP { public delegate bool EnumProc(IntPtr h, IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc p, IntPtr l);
 [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr h, EnumProc p, IntPtr l);
 [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
 [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
 [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
 public static List<string> Top(uint pid){ var r=new List<string>(); EnumWindows((h,l)=>{ uint p; GetWindowThreadProcessId(h,out p); if(p==pid && IsWindowVisible(h)){ var t=new StringBuilder(256); GetWindowText(h,t,256); var c=new StringBuilder(64); GetClassName(h,c,64); r.Add(h.ToInt64()+"|"+c+"|"+t); } return true;}, IntPtr.Zero); return r; }
 public static List<string> Kids(long h){ var r=new List<string>(); EnumChildWindows(new IntPtr(h),(k,l)=>{ var t=new StringBuilder(1024); GetWindowText(k,t,1024); var c=new StringBuilder(64); GetClassName(k,c,64); if(t.Length>0) r.Add(c+"|"+t); return true;}, IntPtr.Zero); return r; }
}
'@
Add-Type -TypeDefinition $src -ErrorAction SilentlyContinue
$p = Get-Process CVLw -ErrorAction SilentlyContinue
if (-not $p) { "CVLw not running"; exit }
$tops = [WP]::Top([uint32]$p.Id)
$tops
foreach ($t in $tops) { $parts = $t.Split('|'); if ($parts[1] -eq '#32770') { "--- children of [$($parts[2])]"; [WP]::Kids([int64]$parts[0]) | Select-Object -First 15 } }
