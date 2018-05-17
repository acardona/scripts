from java.util.concurrent import Executors, TimeUnit
from ini.trakem2 import ControlWindow
from java.lang import System

exe = Executors.newScheduledThreadPool(1)

class Task(Runnable):
  def run(self):
    for project in Project.getProjects():
      project.getLoader().releaseAll()
    System.out.println("Released all")

exe.scheduleWithFixedDelay(Task(), 0, 30, TimeUnit.SECONDS)

