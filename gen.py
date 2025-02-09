# Author: Ankush Gupta
# Date: 2015

"""
Entry-point for generating synthetic text images, as described in:

@InProceedings{Gupta16,
      author       = "Gupta, A. and Vedaldi, A. and Zisserman, A.",
      title        = "Synthetic Data for Text Localisation in Natural Images",
      booktitle    = "IEEE Conference on Computer Vision and Pattern Recognition",
      year         = "2016",
    }
"""

import numpy as np
import h5py
import os, sys, traceback
import os.path as osp
from synthgen import *
from common import *
import wget, tarfile
import pickle as cp
import skimage.io
from PIL import Image


## Define some configuration variables:
NUM_IMG = 1000#-1 # no. of images to use for generation (-1 to use all available):
INSTANCE_PER_IMAGE = 1 # no. of times to use the same image
SECS_PER_IMG = None #max time per image in seconds

# path to the data-file, containing image, depth and segmentation:
DATA_PATH = 'data'
DB_FNAME = osp.join(DATA_PATH,'dset.h5')
# url of the data (google-drive public file):
DATA_URL = 'http://www.robots.ox.ac.uk/~ankush/data.tar.gz'
OUT_FILE = '/Users/alexustian/synth_text_results/SynthTextFull.h5'

PREPROC_DIR = "/Users/alexustian/preprocessed_images"

def get_data():
  """
  Download the image,depth and segmentation data:
  Returns, the h5 database.
  """
  if not osp.exists(DB_FNAME):
    try:
      colorprint(Color.BLUE,'\tdownloading data (56 M) from: '+DATA_URL,bold=True)
      sys.stdout.flush()
      out_fname = 'data.tar.gz'
      wget.download(DATA_URL,out=out_fname)
      tar = tarfile.open(out_fname)
      tar.extractall()
      tar.close()
      os.remove(out_fname)
      colorprint(Color.BLUE,'\n\tdata saved at:'+DB_FNAME,bold=True)
      sys.stdout.flush()
    except:
      print(colorize(Color.RED,'Data not found and have problems downloading.',bold=True))
      sys.stdout.flush()
      sys.exit(-1)
  # open the h5 file and return:
  return h5py.File(DB_FNAME,'r')


def add_res_to_db(imgname,res,db):
  """
  Add the synthetically generated text image instance
  and other metadata to the dataset.
  """
  ninstance = len(res)
  for i in range(ninstance):
    dname = "%s_%d"%(imgname, i)
    db['data'].create_dataset(dname,data=res[i]['img'])
    db['data'].create_dataset(dname+"_mask", data=res[i]['mask'])
    db['data'][dname].attrs['charBB'] = res[i]['charBB']
    db['data'][dname].attrs['wordBB'] = res[i]['wordBB']        
    db['data'][dname].attrs['txt'] = res[i]['txt']


def main(viz=False):
  # open databases:
#  print(colorize(Color.BLUE,'getting data..',bold=True))
#  db = get_data()
#  print(colorize(Color.BLUE,'\t-> done',bold=True))

  # open the output h5 file:
  out_db = h5py.File(OUT_FILE,'w')
  out_db.create_group('/data')
  print(colorize(Color.GREEN,'Storing the output in: '+OUT_FILE, bold=True))

  im_dir = osp.join(PREPROC_DIR, 'bg_img')
  depth_db = h5py.File(osp.join(PREPROC_DIR, 'depth.h5'),'r')
  seg_db = h5py.File(osp.join(PREPROC_DIR, 'seg.h5'),'r')

  imnames = sorted(depth_db.keys())

  with open(osp.join(PREPROC_DIR,'imnames.cp'), 'rb') as f:
    filtered_imnames = set(cp.load(f))

  # get the names of the image files in the dataset:
  N = len(filtered_imnames)
  global NUM_IMG
  if NUM_IMG < 0:
    NUM_IMG = N
  start_idx,end_idx = 0,min(NUM_IMG, N)

  RV3 = RendererV3(DATA_PATH,max_time=SECS_PER_IMG)
  for i in range(start_idx,end_idx):
    if imnames[i] not in filtered_imnames:
        continue
    imname = imnames[i]

    try:
      # get the image:
      img = Image.open(osp.join(PREPROC_DIR, im_dir, imname)).convert('RGB')
#      img = skimage.io.imread(osp.join(PREPROC_DIR, im_dir, imname))

      depth = depth_db[imname][:].T
      depth = depth[:,:,0]

      # get segmentation info:
      seg = seg_db['mask'][imname][:].astype('float32')
      area = seg_db['mask'][imname].attrs['area']
      label = seg_db['mask'][imname].attrs['label']

      # re-size uniformly:
      sz = depth.shape[:2][::-1]
      img = np.array(img.resize(sz,Image.ANTIALIAS))
      seg = np.array(Image.fromarray(seg).resize(sz,Image.NEAREST))

      print(colorize(Color.RED,'%d of %d'%(i,end_idx-1), bold=True))
      res = RV3.render_text(img,depth,seg,area,label,
                            ninstance=INSTANCE_PER_IMAGE,viz=viz)
      if len(res) > 0:
        # non-empty : successful in placing text:
        add_res_to_db(imname,res,out_db)
      # visualize the output:
      if viz:
        if 'q' in input(colorize(Color.RED,'continue? (enter to continue, q to exit): ',True)):
          break
    except:
      traceback.print_exc()
      print(colorize(Color.GREEN,'>>>> CONTINUING....', bold=True))
      continue
#  db.close()
  out_db.close()
  depth_db.close()
  seg_db.close()


if __name__=='__main__':
  import argparse
  parser = argparse.ArgumentParser(description='Genereate Synthetic Scene-Text Images')
  parser.add_argument('--viz',action='store_true',dest='viz',default=False,help='flag for turning on visualizations')
  args = parser.parse_args()
  main(args.viz)
