from pandas import read_csv
import sys
import yaml
from collections import namedtuple, defaultdict
import re
from pathlib import Path

'''
`ErrorData`:
- `dest_file`: The path to the file with links that need to be updated
- `service_dir`: The service directory name for the *link* that needs to be updated, e.g. `rest-services`
- `md_file`: The filename used to get link data from the YAML data file
- `old_link`: The original link
- `new_link`: the replaced link
'''

ErrorData = namedtuple('ErrorData', 'dest_file service_dir md_file old_link new_link') 

def print_error_data(error_data):
    print(f'Error Data:\n\
        destination file:\t{error_data.dest_file}\
    \n\tservice dir:\t\t{error_data.service_dir}\
    \n\tmd file:\t\t{error_data.md_file}\
    \n\told link:\t\t{error_data.old_link}\
    \n\tnew link:\t\t{error_data.new_link}\n\n')


def parse_msg(msg):
    '''Parse data from OBS report'''
    objs = re.match(r'Invalid file link:\(\~\/([-\w]+)\/([-\w]+\/)([-\w]+)\.md\).', msg)
    if objs:
        return objs.group(1), f'{objs.group(3)}.md'
    return None

def fit_array(array, _max):
    n = len(array)
    assert(n <= _max)
    l = []
    for i in range(_max):
        if i < n:
            l.append(array[i])
        else:
            l.append(None)
    return l[0:_max-1]

def get_link_depth(dest_link, new_link):
    dest_glob = list(dest_link.split('/'))
    new_glob = list(new_link.split('/'))
    n = len(dest_glob)
    m = len(new_glob)
    size = max(n, m)

    dest_order = fit_array(dest_glob, size)
    new_order = fit_array(new_glob, size)

    index = 0
    for i in range(size - 1): # don't count filename
        if dest_order[i] == new_glob[i] and dest_order[i] and new_glob[i]:
            index += 1
    return max(0, m - index)
        
def get_link_service_level_depth(service, dest_link):
    dest_glob = list(dest_link.split('/'))
    N = len(dest_glob)
    for i in range(N-1):
        if dest_glob[i] == service:
            return max(0, (N-1) - i)

    
def check_extension(file_name, ext):
    return file_name.split('.')[-1] == ext

    
def get_error_data(df, link_data):
    '''
    Prepares doc data from OBS report and YAML link mapper file
    into `ErrorData` objects to be used to replace links in repo

    - `df` is a Pandas dataframe of OBS linking error info
    - `link_data` is a dict from the YAML link data file
    '''

    for [file, msg] in df[['File','Message']].values:
        print(f'\nunparsing: "{file} -- {msg}"\n')
        parse_data = parse_msg(msg)
        if parse_data and check_extension(file, 'md'):
            
            service_dir, md_file = parse_data

            old_link = f'../{service_dir}/{md_file}'           
            
            dest_file = file.replace('BingMaps', '..')
            
            for service in link_data:
                if service.get('path') == service_dir:
                    # same directory
                    for link_dict in service.get('links'):

                        if link_dict['old-docs'] == md_file:

                            new_link_file = link_dict.get('new-docs')

                            if new_link_file:

                                # depth = get_link_depth(dest_file, f'../{service_dir}/{new_link_file}')
                                
                                depth = get_link_service_level_depth(service_dir, dest_file)

                                rel_path = str.join('/', ['..' for _ in range(depth)]) 
                                
                                new_link = f'{rel_path}/{new_link_file}' #  if depth > 0 else new_link_file.split('/')[-1]
                                
                                datum = ErrorData(dest_file, service_dir, md_file, old_link, new_link)
                                print_error_data(datum)

                                dest_dir = Path(dest_file).parent.absolute()
                                
                                try: 
                                    Path(new_link).parent.relative_to(dest_dir)

                                    datum = ErrorData(dest_file, service_dir, md_file, old_link, new_link)
                                    print(datum)
                                    #yield datum
                                    continue
                                    # exit(0)
                                
                                except ValueError:
                                    print(f'bad data: {dest_file} -- {new_link}')


def update_file(error_object):
    file_name = str(Path(error_object.dest_file).absolute())
    file_str = None
    with open(file_name, 'r', encoding='utf8') as f:
        file_str = f.read()
    file_old = file_str
    file_str = file_str.replace(error_object.old_link, error_object.new_link)
    if file_str != None and file_str != file_old:
        with open(file_name, 'w', encoding='utf8') as f:
            f.write(file_str)
            print(f'Changed file "{error_object.dest_file}": "{error_object.old_link}" --> "{error_object.new_link}"')


'''
def relink_repo(error_data):
    for datum in error_data:
        # get write access to file to change
        file_as_string = None
        with open(get_dest_file_path(data.dist_file), 'w') as dest_f:
            file_as_string = dest_f.read()
            file_as_string.replace(
'''     


if __name__=='__main__':
    print('\nLoading link fixer, usage:\n\n\t$> link_fixer {csv_report_file} {yaml_link_file}\n')
    
    yaml_links = None
    excel_filename = None
    if len(sys.argv) > 2:
        excel_filename = sys.argv[1]
        with open(sys.argv[2], 'r') as f:
            yaml_links = yaml.load(f)
    else:
        exit(1)
        
    df = None
    if excel_filename:
        df = read_csv(excel_filename, sep=',')

    for err_fix in get_error_data(df, yaml_links):
        print(f'\t ---> {err_fix}\n')
        update_file(err_fix)