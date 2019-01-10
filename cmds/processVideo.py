#!/usr/bin/env python3

import http.client, urllib.parse, base64, json
import requests
import argparse
import configparser 
import logging
import os,sys
import gensim.downloader as api
from gensim.models import Word2Vec
import numpy as np
import azure.cosmos.cosmos_client as cosmos_client

_DEFAULT_AS_LOG_LEVEL = 'INFO'
_DEFAULT_AS_LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'
_DEFAULT_AS_CONFIG_LOG_FILE = '~/autoss.log'
_DEFAULT_AS_CONFIG_LOG_LEVEL = 'INFO'

logger = logging.getLogger('autoss')
np.seterr(divide='ignore', invalid='ignore')

def AS_LOG(s):
    sys.stdout.write("{}\n".format(s))
    logger.info(s)

def AS_ERR(s):
    sys.stderr.write("{}\n".format(s))
    logger.error(s)

def init_logger(name, log_file,
                log_level = _DEFAULT_AS_LOG_LEVEL,
                log_format = _DEFAULT_AS_LOG_FORMAT):

    logger = logging.getLogger(name)
    handler = logging.FileHandler(os.path.expanduser(log_file))
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    switcher = {
        'CRITICAL': logging.CRITICAL,
        'ERROR':    logging.ERROR,
        'WARNING':  logging.WARNING,
        'INFO':     logging.INFO,
        'DEBUG':    logging.DEBUG
    }
    logger.setLevel(switcher.get(log_level.upper(),logging.INFO))

class asConfig(object):
    def __init__(self, config_file=None):
        self._config_file = config_file
        self._config_parser = configparser.SafeConfigParser()
        if self._config_file:
            self._config_parser.read(config_file)

    def get_string(self, section, key, default_val=None):
        v =''
        if not self._config_file:
            return default_val
        try:
            v = self._config_parser.get(section, key)
        except configparser.NoOptionError as e:
            v = default_val
        return v

    @property
    def compvision_subkey(self):
        return self.get_string('autoss','azure_compvision_subkey')
    @property
    def compvision_endpoint(self):
        return self.get_string('autoss','azure_compvision_endpoint')
    @property
    def log_file(self):
        return self.get_string('autoss','log_file',_DEFAULT_AS_CONFIG_LOG_FILE)
    @property
    def log_level(self):
        return self.get_string('autoss','log_level',_DEFAULT_AS_CONFIG_LOG_LEVEL)

class asCosmosClient(object):

    def __init__(self, config):
        self._config = config
        # Initialize the Cosmos client
        self._client = cosmos_client.CosmosClient(url_connection=config['ENDPOINT'], auth={
                                    'masterKey': config['PRIMARYKEY']})
        #self._options = {
        #    'offerThroughput': 400
        #}
        #self._container_definition = {
        #    'id': self._config['CONTAINER']
        #}
        self._collection_link = "/dbs/{}/colls/{}".format(
                    self._config['DATABASE'], self._config['CONTAINER'])
   
    def store_document(self, document):
        _newdoc = None
        try:
            _newdoc = self._client.CreateItem(self._collection_link,document)
        except Exception as e:
            AS_ERR("Cosmos DB store_document error:{}".format(e))
        return _newdoc

    def get_document(self, video_name, camera_no, frame_no):
        options = {}
        options['enableCrossPartitionQuery'] = True
        options['maxItemCount'] = 1 
        partition_key=None
        query = {'query': "SELECT * FROM s WHERE s.video='{}' and s.camera_no='{}' and s.frame_no='{}'".format(video_name, camera_no, frame_no)}
        try:
            docs_iterable = self._client.QueryItems(self._collection_link, query, options, partition_key)
            if len(list(docs_iterable)) > 0:
                return docs_iterable.fetch_next_block()[0]
        except Exception as e:
            AS_ERR("Cosmos DB get_document error ({} {} {}):{}".format(video_name, camera_no, frame_no, e))
        return None

import glob
def glob_image_files(mypath):
    return glob.glob('{}/*.jpg'.format(mypath))

def get_tags(compvision_endpoint, subscription_key, image_file):
    # Request headers
    headers = {
        'Content-Type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': subscription_key,
    }
    # Request parameters
    params = urllib.parse.urlencode({
        # All of them are optional
        #'visualFeatures': 'Tags',
        'visualFeatures': 'Description',
        'language': 'en',
    })

    tagsets = []
    try:
        with open(image_file, 'rb') as f:
            img_data = f.read()
            api_url = "{}/vision/v2.0/analyze?{}".format(compvision_endpoint, params)
            #AS_LOG("API URL:{}".format(api_url))
            r = requests.post(api_url,
                    headers=headers,
                    data=img_data)
            raw_parsed = r.json()
            #tags = [d.get('name') for d in tagsets]
            ## [Data Structure]
            ## raw_parsed['tags'] = [
            ##  {"name": "tagname1", "confidence":0.9999},
            ##  {"name": "tagname2", "confidence":0.9999},
            ##  ...]
            #tagsets = raw_parsed['tags']
            tagsets = raw_parsed['description']['tags']
    except Exception as e:
        AS_ERR("Error:{}".format(e))

    return tagsets


def main():

    parser = argparse.ArgumentParser(description='This script is ...')
    parser.add_argument('--config', help='config file (default autoss.conf)')
    parser.add_argument('-n','--name', help='video name')
    parser.add_argument('-c','--camerano', help='video name')
    parser.add_argument('-d','--framedir', help='video frame images directory path')
    args = parser.parse_args()

    if not args.name or not args.camerano or not args.framedir:
        print(parser.parse_args(['-h']))
        sys.exit(1) 

    video_name = args.name
    camera_no = args.camerano
    frame_dir = args.framedir
    config_file = "autoss.conf"
    if args.config:
        config_file = args.config

    config = asConfig(config_file)
    init_logger('autoss', config.log_file, config.log_level)

    subscription_key = config.compvision_subkey
    compvision_endpoint= config.compvision_endpoint
    word2vec_model_file ="{}/../assets/{}".format(
                os.getcwd(),
                config.get_string("autoss", "word2vec_model_file"))
    AS_LOG("Reading word2vec_model_file:{}".format(word2vec_model_file))
    model = Word2Vec.load(word2vec_model_file)
    AS_LOG("Reading subscription_key:{}".format(subscription_key))
    AS_LOG("Reading compvision_endpoint:{}".format(compvision_endpoint))

    cosmos_config_vectors = {
        'ENDPOINT': config.get_string("autoss", "cosmos_endpoint_vectors"),
        'PRIMARYKEY': config.get_string("autoss","cosmos_primarykey_vectors"),
        'DATABASE': config.get_string("autoss","cosmos_db_vectors"),
        'CONTAINER': config.get_string("autoss","cosmos_col_vectors")
    }
    cosmos_config_rnninput = {
        'ENDPOINT': config.get_string("autoss","cosmos_endpoint_rnninput"),
        'PRIMARYKEY': config.get_string("autoss","cosmos_primarykey_rnninput"),
        'DATABASE': config.get_string("autoss","cosmos_db_rnninput"),
        'CONTAINER': config.get_string("autoss","cosmos_col_rnninput")
    }
    cosmos_vectors_client = asCosmosClient(cosmos_config_vectors)
    cosmos_rnninput_client = asCosmosClient(cosmos_config_rnninput)

    ## Iterate image files
    image_files = glob_image_files(frame_dir)    

    frames = {}
    frame_no_list=[]
    ## Populate verified frames
    for image_file in image_files:
        t = image_file.split('/')
        imagefile_no_ext = t[-1].replace('.jpg', '')
        c = imagefile_no_ext.split('_')
        if len(c)!=3:
            AS_ERR(f"Invalid file name format: {image_file}! "
                   f"Image name should be <NAME>_<CAMERANO>_<FRAMENO>.<ext>")
            continue
        _video_name=c[0]
        _camera_no=int(c[1])
        _frame_no=int(c[2])
        if _video_name != video_name or _camera_no != int(camera_no):
            AS_ERR(f"Invalid file name format: {image_file}!")
            continue
        frames[_frame_no] = image_file
        frame_no_list.append(_frame_no)
    AS_LOG("frame count={}".format(len(frame_no_list)))
    ## Sort frame_no_list
    frame_no_list.sort()

    ## Iterate frames and do the following:
    ## - Get tags for each frame via Computer Vision API
    ## - Get vector for each tag using Word2Vec
    ## - Get sum of tag vectors
    for frame_no in frame_no_list:
        # continue  # Only for debug 

        image_file = frames[frame_no]
        AS_LOG("Processing frame: {}".format(image_file))

        ## Get tags via Computer Vision service
        tagsets = get_tags(compvision_endpoint, subscription_key, image_file)

        vectors_outdata = {}
        vectors_outdata['id'] = "{}_{}_{}".format(video_name,camera_no,frame_no)
        vectors_outdata['video'] = video_name
        vectors_outdata['camera_no'] = camera_no
        vectors_outdata['frame_no'] = str(frame_no)

        ## Get Vectors for each tags
        vectors = {}
        sumvector = np.zeros(100)
        output_tagsets=[]
        for tag in tagsets:
            # Check if tag work exists in the model
            try:
                v = model[tag]
            except KeyError:
                logging.error("Skip:{} is not the model".format(tag))
                continue
            tagvector = np.array(list(v))
            sumvector = sumvector + tagvector
            vectors[tag] = tagvector.tolist()
            output_tagsets.append(tag)
            # logging.info("tag->{}".format(tag))
            # logging.info(vectors[tag])
        vectors_outdata['vectors'] = vectors
        vectors_outdata['sumvector'] = sumvector.tolist()
        vectors_outdata['tags'] = output_tagsets
        #print(json.dumps(vectors_outdata))
        
        ## Store in CosmosDB (db:vectors)
        cosmos_vectors_client.store_document(vectors_outdata)

    ## Iterate frames and do the following:
    for frame_no in frame_no_list:
        AS_LOG("Processing vector computations for frame: {}".format(frame_no))
        # Check if there is next scene frame
        next_frame_no = frame_no + 1
        if next_frame_no > len(frame_no_list):
            break
        ## Get current frame and next frame document from Cosmos DB
        cur_doc = cosmos_vectors_client.get_document(
                    video_name, camera_no, str(frame_no))
        next_doc = cosmos_vectors_client.get_document(
                    video_name, camera_no, str(next_frame_no))
        if not cur_doc:
            AS_ERR("Error missing frame: {} {} {}! So skip".format(video_name, camera_no,frame_no))
            continue
        if not next_doc:
            AS_ERR("Error missing frame: {} {} {}! So skip".format(video_name, camera_no,next_frame_no))
            continue
        cur_sumvector = cur_doc["sumvector"]
        next_sumvector = next_doc["sumvector"]

        ## REQ2: Get diff vector
        ## diffvector(T) = Xpgm,C1,C2(T+1) - Xpgm,C1,C2(T)
        diffvector = np.zeros(100)
        try:
            diffvector = np.array(next_sumvector) - np.array(cur_sumvector)         
        except Exception as e:
            AS_ERR("Errors in diff vector computation: {}".format(e))

        ## REQ3: Get norm vector of diff vector
        ## normvector(T) = norm (diff_vector(T))
        normvector = np.zeros(100)
        try:
            if not (diffvector == np.zeros(100)).all():
                normvector = ( diffvector / np.linalg.norm(diffvector) ).all()
        except Exception as e:
            AS_ERR("Errors in norm vector computation: {}".format(e))

        ## REQ4: Counter
        ## NOT IMPLEMENTED AT THIS POINT
    
        rnninput_outdata = {}
        rnninput_outdata['id'] = "{}_{}_{}".format(video_name,camera_no,frame_no)
        rnninput_outdata['video'] = video_name
        rnninput_outdata['camera_no'] = camera_no
        rnninput_outdata['frame_no'] = str(frame_no)
        rnninput_outdata['sumvector'] = cur_sumvector
        rnninput_outdata['diffvector'] = diffvector.tolist()
        rnninput_outdata['normvector'] = normvector.tolist()

        ## Store in CosmosDB (db:rnninput)
        cosmos_rnninput_client.store_document(rnninput_outdata)

    AS_LOG("Done!")

if __name__ == '__main__':
    main()
