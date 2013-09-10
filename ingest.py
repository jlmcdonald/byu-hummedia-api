import shlex
from subprocess import Popen, PIPE, STDOUT
from gearman import GearmanWorker
from hummedia.config import GEARMAN_SERVERS, MEDIA_DIRECTORY

worker = GearmanWorker(GEARMAN_SERVERS)

# Pass the unique ID of the media to this task to run it (e.g., 1234)
def generate_webm(gearman_worker, gearman_job):
    newfile = MEDIA_DIRECTORY + gearman_job.data

    print "TASK RECEIVED FOR %s" % newfile # @TODO timestamp

    # CONVERT TO WEBM
    cmd = "avconv -threads auto -i %s.mp4 -c:v libvpx -crf 10 \
           -b:v 768K -c:a libvorbis -deadline realtime \
           -cpu-used -10 %s.webm" % (newfile, newfile)
    cmd = cmd.encode('utf-8')

    response = Popen(shlex.split(cmd), stdout=PIPE, stdin=PIPE, stderr=STDOUT)
    response.wait()

    if response.returncode != 0:
        print "TASK FAILURE" # @TODO timestamp
        return "ERROR" # @TODO return something more specific to the client
                
    chmod(newfile + ".webm", 0775)

    print "TASK COMPLETE" # @TODO timestamp
    return "COMPLETE" # @TODO return something more specific to the client

worker.register_task("generate_webm", generate_webm)

worker.work()
