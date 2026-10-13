"""Ejecuta el notebook con el Python actual y exporta un informe sin código."""
from pathlib import Path
import json
import sys
import tempfile

import nbformat
from nbclient import NotebookClient
from nbconvert import HTMLExporter
from jupyter_client import KernelManager
from jupyter_client.kernelspec import KernelSpecManager


def main():
    project = Path(__file__).resolve().parent
    notebook_path = project / 'EDA_Combustibles.ipynb'
    notebook = nbformat.read(notebook_path, as_version=4)
    with tempfile.TemporaryDirectory(prefix='eda-combustibles-') as temporary:
        work = Path(temporary)
        kernel_dir = work / 'kernels' / 'eda'
        kernel_dir.mkdir(parents=True)
        kernel = {'argv': [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
                  'display_name': 'EDA (Python actual)', 'language': 'python',
                  'env': {'IPYTHONDIR': str(work / 'ipython'), 'MPLCONFIGDIR': str(work / 'matplotlib')}}
        (kernel_dir / 'kernel.json').write_text(json.dumps(kernel), encoding='utf-8')
        manager = KernelManager(kernel_name='eda',
                                kernel_spec_manager=KernelSpecManager(kernel_dirs=[str(work / 'kernels')]))
        client = NotebookClient(notebook, km=manager, timeout=180,
                                resources={'metadata': {'path': str(project)}})
        try:
            client.execute()
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
            manager.cleanup_resources()
    nbformat.validate(notebook)
    nbformat.write(notebook, notebook_path)
    exporter = HTMLExporter(template_name='lab', exclude_input=True,
                            exclude_input_prompt=True, exclude_output_prompt=True)
    html, _ = exporter.from_notebook_node(notebook, resources={
        'metadata': {'name': 'EDA de combustibles — Álvaro Quero Sandoval'}})
    (project / 'informe.html').write_text(html, encoding='utf-8')
    code_cells = [c for c in notebook.cells if c.cell_type == 'code']
    print(f'Ejecución completa: {len(code_cells)} celdas de código. Informe: {project / "informe.html"}')


if __name__ == '__main__':
    main()
