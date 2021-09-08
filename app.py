from flask import Flask, abort
from flask import jsonify
import json
from PIL import Image
from pymongo import MongoClient
from pymongo.uri_parser import _parse_options
from random import randrange
import ipfshttpclient
import os
import urllib.request, json

app = Flask(__name__)


########################################################################
# Data
########################################################################

# opensea-creatures

BACKGROUND = ["GREEN", "RED"]

GENDER = ["MALE", "FEMALE"]

MALE_SKIN = ["value"]
MALE_HAIRS = ["BEANIE"]
MALE_EYES = [""]
MALE_MOUTH = ["BIG-GRIN"]
MALE_CLOTHS = ["PULLOVER-HOODIE"]

FEMALE_SKIN = ["PERU"]
FEMALE_HAIRS = ["PONY-BANG", "SIDE-BRAID"]
FEMALE_EYES = ["REGULAR", "WINK"]
FEMALE_MOUTH = ["CLOSED", "PURPLE"]
FEMALE_CLOTHS = ["CYBER", "SILVER"]


# opensea-creatures-accessories

# contractURI() support

CONTRACT_URI_METADATA = {
    "opensea-creatures": {
        "name": "OpenSea Creatures",
        "description": "Friendly creatures of the sea.",
        "image": "https://example.com/image.png",
        "external_link": "https://github.com/ProjectOpenSea/opensea-creatures/",
    },
    "opensea-erc1155": {
        "name": "OpenSea Creature Accessories",
        "description": "Fun and useful accessories for your OpenSea creatures.",
        "image": "https://example.com/image.png",
        "external_link": "https://github.com/ProjectOpenSea/opensea-erc1155/",
    },
}
CONTRACT_URI_METADATA_AVAILABLE = CONTRACT_URI_METADATA.keys()


########################################################################
# Routes
########################################################################


def deployOnIpfs(imageLocation):
    api = ipfshttpclient.connect(os.environ["IPFSCLIENT"])
    res = api.add(imageLocation)
    res2 = api.pin.add(res["Hash"])
    print("===================>   %s   <========================" % res2)
    return res["Hash"]


def deployMetaDataToIpfs(data):
    with open("metadata.json", "w") as write_file:
        json.dump(data, write_file)
    api = ipfshttpclient.connect(os.environ["IPFSCLIENT"])
    res = api.add("metadata.json")
    return res["Hash"]


def getrandom(max):
    irand = randrange(0, int(max))
    return irand


def gethash(value):
    return hash(value)


def HashCheckFromMongo(hash):
    client = MongoClient(os.environ["MONGODBKEY"])
    mydb = client.nft
    hashes = mydb.hashes
    result = hashes.find_one({"hash": hash})
    if result is None:
        return True
    else:
        return False


def fetchHttpresponse(Url):
    with urllib.request.urlopen(Url) as url:
        data = json.loads(url.read().decode())
        return data


def checkToken(token_id):
    client = MongoClient(os.environ["MONGODBKEY"])
    mydb = client.nft
    data = mydb.metadata
    result = data.find_one({"id": int(token_id)})
    print("======================= check result : ", result)
    if result == None:
        return False
    else:
        return True


def insertTokenData(token_id, LinkOfmetadata):
    client = MongoClient(os.environ["MONGODBKEY"])
    mydb = client.nft
    data = mydb.metadata
    result = data.insert_one({"id": int(token_id), "metadatalink": LinkOfmetadata})
    print("data added sucessfully : ", result)


def getTokenData(token_id):
    client = MongoClient(os.environ["MONGODBKEY"])
    mydb = client.nft
    data = mydb.metadata
    result = data.find_one({"id": int(token_id)})
    return result


@app.route("/")
def basic():
    return jsonify({"res": "invalid url"})


@app.route("/api/creature/<token_id>")
def creature(token_id):
    if checkToken(token_id):
        data = getTokenData(token_id)
        return fetchHttpresponse(data["metadatalink"])
    else:
        while True:
            token_id = int(token_id)
            gender = GENDER[getrandom(len(GENDER))]
            skin = None
            background = None
            hairs = None
            eyes = None
            mouth = None
            cloths = None
            if gender == GENDER[0]:
                skin = MALE_SKIN[getrandom(len(MALE_SKIN))]
                background = BACKGROUND[getrandom(len(BACKGROUND))]
                hairs = MALE_HAIRS[getrandom(len(MALE_HAIRS))]
                eyes = MALE_EYES[getrandom(len(MALE_EYES))]
                mouth = MALE_MOUTH[getrandom(len(MALE_MOUTH))]
                cloths = MALE_CLOTHS[getrandom(len(MALE_CLOTHS))]
            elif gender == GENDER[1]:
                background = BACKGROUND[getrandom(len(BACKGROUND))]
                skin = FEMALE_SKIN[getrandom(len(FEMALE_SKIN))]
                hairs = FEMALE_HAIRS[getrandom(len(FEMALE_HAIRS))]
                eyes = FEMALE_EYES[getrandom(len(FEMALE_EYES))]
                mouth = FEMALE_MOUTH[getrandom(len(FEMALE_MOUTH))]
                cloths = FEMALE_CLOTHS[getrandom(len(FEMALE_CLOTHS))]

            checkUnique = background + skin + hairs + eyes + mouth + cloths

            if HashCheckFromMongo(gethash(checkUnique)):
                break
        gender = gender.lower()
        image_url = _compose_image(
            [
                "images/background/{}.png".format(background),
                "images/{}/skin/{}.png".format(gender, skin),
                "images/{}/hairs/{}.png".format(gender, hairs),
                "images/{}/eyes/{}.png".format(gender, eyes),
                "images/{}/mouth/{}.png".format(gender, mouth),
                "images/{}/cloths/{}.png".format(gender, cloths),
            ],
            token_id,
        )

        attributes = []
        _add_attribute(attributes, "GENDER", gender, token_id)
        _add_attribute(attributes, "Eyes", eyes, token_id)
        _add_attribute(attributes, "mouth", mouth, token_id)
        _add_attribute(attributes, "Cloths", cloths, token_id)

        data = {
            "Token id ": token_id,
            "description": "Nft tokens made ",
            "image": image_url,
            "external_url": "https://openseacreatures.io/%s" % token_id,
            "attributes": attributes,
        }
        tokenUri = "https://gateway.ipfs.io/ipfs/%s" % deployMetaDataToIpfs(data)
        insertTokenData(token_id, tokenUri)
        return fetchHttpresponse(tokenUri)


#

# contractURI()


@app.route("/contract/<contract_name>")
def contract_uri(contract_name):
    if not contract_name in CONTRACT_URI_METADATA_AVAILABLE:
        abort(404, description="Resource not found")
    return jsonify(CONTRACT_URI_METADATA[contract_name])


# Error handling


@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404


########################################################################
# Utility code
########################################################################


def _add_attribute(existing, attribute_name, options, token_id, display_type=None):
    trait = {"trait_type": attribute_name, "value": options}
    if display_type:
        trait["display_type"] = display_type
    existing.append(trait)


def _compose_image(image_files, token_id, path="creature"):
    composite = None
    for image_file in image_files:
        foreground = Image.open(image_file).convert("RGBA")

        if composite:
            composite = Image.alpha_composite(composite, foreground)
        else:
            composite = foreground

    output_path = "images/output/%s.png" % token_id
    composite.save(output_path)
    Hash = deployOnIpfs(output_path)
    return "https://gateway.ipfs.io/ipfs/%s" % Hash


def HashCheckFromMongo(hash):
    client = MongoClient(os.environ["MONGODBKEY"])
    mydb = client.nft
    hashes = mydb.hashes
    result = hashes.find_one({"hash": hash})
    if result == None:
        result = hashes.insert_one({"hash": hash})
        print(result)
        return True
    else:

        return False


if __name__ == "__main__":
    app.run(debug=True, use_reloader=True)
