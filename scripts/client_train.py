# inside hda python script - for training
# pythonSOP path: /obj/rndForest/rndforest/train

import hou
import pandas as pd
import tempfile
import os
import requests

node = hou.pwd()
geo = node.geometry()
do_train = node.parent().parm("do_train").eval()  # from HDA parameter

def train(do_train=False):
    if do_train:
        positions = []
        classes = []

        for pt in geo.points():
            pos = pt.position()
            positions.append([pos[0], pos[1], pos[2]])
            classes.append(pt.intAttribValue('rndf_class'))

        df = pd.DataFrame(positions, columns=['x1', 'x2', 'x3'])
        df['class'] = classes

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            df.to_csv(tmp.name, index=False)
            csv_path = tmp.name

        url = f"{hou.getenv('RNDFOREST_API_URL')}/train?force=true"  # always force from button
        with open(csv_path, 'rb') as f:
            files = {'file': f}
            r = requests.post(url, files=files)
            print("Training result:", r.json())

        os.remove(csv_path)
    else:
        return

train(do_train)
