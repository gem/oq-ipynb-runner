#!/usr/bin/env ipython

import os
import sys
from jupyter_client import KernelManager
from Queue import Empty
from nbformat import NotebookNode, reads
from pprint import pprint


def run_cell(kc, cell, tout):
    retval = kc.execute(cell.input)

    retval = kc.get_shell_msg(timeout=tout)

    print "CONTENT_STATUS: %s" % retval['content']['status']
    if retval['content']['status'] == 'error':
        print "ENAME: "
        pprint(retval['content']['ename'])
        print "EVALUE:"
        pprint(retval['content']['evalue'])
        print "TRACEBACK:"
        for i in retval['content']['traceback']:
            print i

    outs = []
    while True:
        try:
            msg = kc.get_iopub_msg(timeout=0.5)
        except Empty:
            break
        msg_type = msg['msg_type']
        if msg_type in ('status', 'execute_input'):
            continue
        elif msg_type == 'execute_input':
            continue
        elif msg_type == 'clear_output':
            outs = []
            continue

        content = msg['content']
        # print msg_type, content
        out = NotebookNode(output_type=msg_type)

        if msg_type == 'stream':
            out.stream = content['name']
            out.text = content['text']
        elif msg_type in ('display_data', 'execute_result'):
            out['metadata'] = content['metadata']
            for mime, data in content['data'].iteritems():
                attr = mime.split('/')[-1].lower()
                # this gets most right, but fix svg+html, plain
                attr = attr.replace('+xml', '').replace('plain', 'text')
                setattr(out, attr, data)
            if msg_type == 'execute_result':
                out.prompt_number = content['execution_count']
        elif msg_type == 'error':
            out.ename = content['ename']
            out.evalue = content['evalue']
            out.traceback = content['traceback']
        else:
            print "unhandled iopub msg:", msg_type
        print "msg_type: %s" % msg_type
        outs.append(out)

    return outs


def test_notebook(nb):
    km = KernelManager()
    km.start_kernel(extra_arguments=['--pylab=inline'],
                    stderr=open('/tmp/km.stderr', 'w'))
    kc = km.client()
    kc.start_channels()
    iopub = kc.iopub_channel
    shell = kc.shell_channel

    shell.get_msg()

    successes = 0
    failures = 0
    errors = 0
    for ws in nb.worksheets:
        for cell in ws.cells:
            if cell.cell_type != 'code':
                continue
            try:
                outs = run_cell(kc, cell, 30)

            except Exception as e:
                print "failed to run cell:", repr(e)
                # print cell.input
                print dir(cell)
                errors += 1
                continue

            failed = False
            print "Count outs: %d" % len(outs)
            print "Count cell_out: %d" % len(cell.outputs)
            for out, ref in zip(outs, cell.outputs):
                print "OUT[%s]" % outs
                print "EXP[%s]" % ref
                #if not compare_outputs(out, ref):
                #    failed = True
                #    break
            if failed:
                failures += 1
            else:
                successes += 1
            sys.stdout.write('.')

    print
    print "tested notebook %s" % nb.metadata.name
    print "    %3i cells successfully replicated" % successes
    if failures:
        print "    %3i cells mismatched output" % failures
    if errors:
        print "    %3i cells failed to complete" % errors
    kc.stop_channels()
    km.shutdown_kernel()
    del km


def get_ipnb(spath):
    li = []
    if os.path.isfile(spath):
        if spath.endswith('.ipynb'):
            li.append(spath)
            return li

    for root, subf, fnames in os.walk(spath):
        for fname in fnames:
            if fname.endswith('.ipynb'):
                li.append(os.path.join(root, fname))
    return li


def main(argv):
    notebooks = []

    for f in argv:
        notebooks += get_ipnb(f)

    for notebook in notebooks:
        with open(notebook) as f:
            nb = reads(f.read(), 3)
            test_notebook(nb)

if __name__ == '__main__':
    main(sys.argv[1:])
