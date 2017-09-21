import os
import re
import sublime
import sublime_plugin

class CheckIobCommand(sublime_plugin.TextCommand):

    def check_iob_connection(self):
        ports = [p.name for p in self.port_list]

        rtl_gb = sublime.load_settings('check-iob.sublime-settings').get('rtl_gb', 'rtl_gb')
        netlist = sublime.load_settings('check-iob.sublime-settings').get('netlist', 'syn/results/latest')

        iob_file = self.view.file_name().replace('/'+rtl_gb+'/', '/'+netlist+'/').replace('.sv', '.v')
        if not os.path.exists(iob_file):
            self.error = 'cannot find iob netlist ' + iob_file
            return False

        iob_name = iob_file.split('/')[-1][:-2]
        iob = open(iob_file, 'r+').read()
        pattern = r'module\s+[a-zA-Z0-9_]+\s+\(((\s+[a-zA-Z0-9_]+,?)+)\s+\);'
        s = re.findall(pattern, iob)
        netlist_ports = list(map(lambda s: s.strip(), s[0][0].split(',')))
        if len(netlist_ports) != len(ports):
            self.error = iob_name + ' not passed. ' + 'netlist and rtl have different ports.'
            return False

        ports = {}
        for match in re.findall(r'(?:input|output)\s*(\[\d+:\d+\])*\s*([a-zA-Z0-9_, \n]+);', iob):
            if not match[0]:
                width = 1
            else:
                width = int(match[0][1:-1].split(':')[0])+1

            ports[width] = ports.get(width, [])
            ports[width] += list(map(lambda s: s.strip(), match[1].split(',')))
        for w, p in ports.items():
            for one_port in p:
                found = re.findall(r'\(\s*'+one_port+r'(?:\[(\d+)\])?\s*\)', iob)
                if w > 1:
                    found = list(map(int, found))
                    found_unconnected = any(i not in range(w) for i in found)
                else:
                    found_unconnected = not bool(found)
                if found_unconnected:
                    self.error = iob_name + ' not passed. ' + 'found unconnected port: ' + one_port
                    return False
        return True

    def description(self):
        if hasattr(self, 'error'):
            return 'Check iob ERROR: '+self.error
        else:
            return 'iob check passed'

    def is_enabled(self):
        self.current_file_name = self.view.file_name()
        if not self.current_file_name.endswith('.sv'):
            self.error = 'This is not a .sv file.'
            return False

        self.get_sv_source()
        self.get_ports()
        self.passed = self.check_iob_connection()
        return self.passed

    def get_sv_source(self):
        with open(self.current_file_name, 'r') as fp:
            self.sv_source = fp.read().replace('logic', '')

    def get_ports(self):
        space = r'[ ]*'
        io = r'(input|output)'
        pwidth = r'((?:[ ]+\[.+\])*)'
        name = r'([\w_]+)'
        psize = r'((?:[ ]+\[.+\])*)'
        pattern = re.compile('(' + space.join(['^', io, pwidth, name, psize]) + ')', flags=re.MULTILINE)
        self.port_list = []
        class Port(object):
            pass
        for line in pattern.findall(self.sv_source):
            port = Port()
            port.io, port.width, port.name, port.size = line[1:]
            port.width = port.width.replace(' ', '')
            port.size = port.size.replace(' ', '')
            self.port_list.append(port)
