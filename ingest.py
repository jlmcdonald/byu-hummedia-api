#!/usr/bin/python

import os
from hummedia import app
from hummedia.config import GEARMAN_SERVERS, MEDIA_DIRECTORY

# Pass the unique ID of the media to this task to run it (e.g., 1234)
def generate_webm(gearman_worker=None, gearman_job=None, file_id=None):
    if file_id is not None:
        newfile = MEDIA_DIRECTORY + file_id
    else:
        newfile = MEDIA_DIRECTORY + gearman_job.data

    print "TASK RECEIVED FOR %s" % newfile # @TODO timestamp

    # CONVERT TO WEBM
    cmd = "avconv -threads auto -i %s.mp4 -c:v libvpx -crf 10 \
           -b:v 768K -c:a libvorbis -deadline realtime \
           -cpu-used -10 %s.webm" % (newfile, newfile)
    cmd = cmd.encode('utf-8')

    result = os.system(cmd)
    
    if result != 0:
        print "TASK FAILURE" # @TODO timestamp
        return "ERROR" # @TODO return something more specific to the client
                
    os.chmod(newfile + ".webm", 0775)

    print "TASK COMPLETE" # @TODO timestamp
    return "COMPLETE" # @TODO return something more specific to the client



if not app.config.get('TESTING'):
  from gearman import GearmanWorker
  worker = GearmanWorker(GEARMAN_SERVERS)
  worker.register_task("generate_webm", generate_webm)
  worker.work()
