import os
import re
from datetime import datetime
import gzip
import shutil
import time

class RotatingFileWriter:
    def __init__(self, base_name="output", ext=".txt", max_size=10*1024*1024, gzip_files=True, header = ""):
        self.base_name = base_name
        self.ext = ext
        self.max_size = max_size
        self.gzip_files = gzip_files
        self.date = datetime.now().strftime("%Y%m%d")
        self.run_number = self._get_next_run_number()
        self.cycle_number = 1
        self.current_size = 0
        self.header = header
        self.open_new_file()

    def _get_next_run_number(self):
        """Find the next available run number across all files."""
        run_pattern = re.compile(
            rf"{self.base_name}_(\d+)_run(\d+)_cycle\d+{self.ext}$"
        )
        max_run = 0
        for fname in os.listdir("."):
            match = run_pattern.match(fname)
            if match:
                run_num = int(match.group(2))
                max_run = max(max_run, run_num)
        return max_run + 1

    def open_new_file(self):
        if hasattr(self, "file") and self.file:
            self._close_and_gzip()
        self.filename = (
            f"{self.base_name}_{self.date}_run{self.run_number}_cycle{self.cycle_number}{self.ext}"
        )
        self.file = open(self.filename, "w", buffering=1024*1024)
        if self.header:
            self.file.write(self.header + "\n")   # <-- write header line
            self.current_size = len(self.header) + 1
        else:
            self.current_size = 0
        print(f"[INFO] Opened {self.filename}")
        self.cycle_number += 1
        time.sleep(1)

    def _close_and_gzip(self):
        """Close the current file and optionally gzip it."""
        self.file.close()
        if self.gzip_files:
            gz_filename = self.filename + ".gz"
            with open(self.filename, 'rb') as f_in, gzip.open(gz_filename, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            os.remove(self.filename)  # remove original uncompressed file
            print(f"[INFO] Compressed {self.filename} -> {gz_filename}")

    def write(self, data: str):
        encoded = data.encode()
        size = len(encoded)
        if self.current_size + size > self.max_size:
            self.open_new_file()
        self.file.write(data)
        self.current_size += size

    def close(self):
        if self.file:
            self._close_and_gzip()

writer = RotatingFileWriter(base_name="gps_daq", ext=".txt", max_size=1024*1024, header = "hello")  # 1 MB max

try:
    k = ""
    for i in range(10000):
        j = str(i)
        writer.write(f"Line {k+j}\n")
        k = k+j

except KeyboardInterrupt:
    print("DAQ Stopped")

finally:
    writer.close()
