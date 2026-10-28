"""Install/compile the read-only exporter. Attaching it in MT5 is a separate step."""
from pathlib import Path
import argparse, shutil, subprocess, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from qros.config.settings import Settings

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--terminal-data-dir',type=Path,required=True)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1];settings=Settings()
    data=args.terminal_data_dir.resolve(strict=True)
    if not (data/'MQL5').is_dir():raise ValueError('Choose the data directory shown by MT5 File > Open Data Folder')
    if not settings.mt5_path:raise ValueError('Configure QROS_MT5_PATH first')
    editor=Path(settings.mt5_path).parent/'MetaEditor64.exe'
    if not editor.is_file():raise ValueError('MetaEditor not found beside configured terminal')
    source=data/'MQL5/Experts/QROS/QROSCalendarExport.mq5'
    source.parent.mkdir(parents=True,exist_ok=True)
    if source.exists() and source.read_bytes()!=(root/'mt5/QROSCalendarExport.mq5').read_bytes():
        raise ValueError('Installed exporter differs; back it up and review before replacing')
    shutil.copy2(root/'mt5/QROSCalendarExport.mq5',source)
    log=root/'var/readiness/calendar_compile.log';log.parent.mkdir(parents=True,exist_ok=True)
    command=f'"{editor}" /compile:"{source}" /log:"{log}"'
    subprocess.run(command,timeout=120,check=True)
    text=log.read_text(encoding='utf-16')
    if '0 errors, 0 warnings' not in text or not source.with_suffix('.ex5').is_file():
        raise RuntimeError('Compilation not verified; inspect '+str(log))
    print('Read-only exporter compiled. Attach QROSCalendarExport to a dedicated chart in the configured MT5 terminal.')
    print('Set QROS_NEWS_CALENDAR_PATH='+str(data/'MQL5/Files/QROS/calendar.json'))
    print('No trading permission or account configuration was changed.')

if __name__=='__main__':main()
