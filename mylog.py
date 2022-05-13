import logging
import inspect
import os
import pathlib

def my_log(msg:str,level:str="INFO"):
    stack = inspect.stack()
    stack = stack[1:-1]
    file_name = [ item[1].split('\\')[-1][:-3]
                 for item in stack ]
    function_name = [ item[3] for item in stack ]
    trace = zip(file_name,function_name)
    trace = [":".join(pair) for pair in trace]
    trace = " <- ".join(trace)
    result = "|| " + f"{msg:<50}" + ' || ' + trace
    if level.upper() == "INFO":
        logging.info(result)
    elif level.upper() == "DEBUG":
        logging.debug(result)
    elif level.upper() == "WARN":
        logging.warn(result)
    else:
        logging.warn(result)
        my_log("WRONG LEVEL SETTING PASSED TO MY_LOG","WARN")

def my_exception(e:Exception,msg:str):
    my_log(f"{type(e)}\n          ||{str(e)}\n          || {msg}","WARN")

def my_hr(msg:str=""):
    logging.info(f"{'- '+msg+' -':^50}")

logging.getLogger("urllib3").propagate = False
filename = p = os.path.join(pathlib.Path(__file__).parent.resolve(), 
                    "LOG")
logging.basicConfig(handlers=[logging.FileHandler(filename="LOG", 
                                                 encoding='utf-8', mode='a+')],
                    level=logging.DEBUG,
                    format="[%(levelname)-7s] %(asctime)s %(message)s",
                    datefmt="%b-%d %H:%M:%S")
print("logging redirected to LOG")