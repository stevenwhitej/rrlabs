#!/usr/bin/env python3
""" API
    Methods:
    - GET /api/objects - Retrieves a list of objects
    - GET /api/objects/1 - Retrieves a specific objects
    - POST /api/objects - Creates a new object
    - PUT /api/objects/1 - Edits a specific object
    - DELETE /api/objects/1 - Deletes a specific object
    Return codes:
    - 200 success - Request ok
    - 201 success - New objects has been created
    - 400 bad request - Input request not valid
    - 401 unauthorized - User not authenticated
    - 403 forbidden - User authenticated but not authorized
    - 404 fail - Url or object not found
    - 405 fail - Method not allowed
    - 409 fail - Object already exists, cannot create another one
    - 422 fail - Input data missing or not valid
    - 500 error - Server error, maybe a bug/exception or a backend/database error
"""
__author__ = 'Andrea Dainese <andrea.dainese@gmail.com>'
__copyright__ = 'Andrea Dainese <andrea.dainese@gmail.com>'
__license__ = 'https://creativecommons.org/licenses/by-nc-nd/4.0/legalcode'
__revision__ = '20170105'

import configparser, flask, functools, logging, os.path
from api_modules import *

config = configparser.ConfigParser()
config_file = '/data/etc/controller.ini'
if os.path.isfile(config_file):
    config.read(config_file)
else:
    config.add_section('controller')
    config.set('controller', 'id', 0)
    config.write(config_file)
controller_id = int(config['controller']['id'])

@app.errorhandler(400)
def http_401(err):
    response = {
        'code': 400,
        'status': 'bad request',
        'message': str(err)
    }
    return flask.jsonify(response), response['code']

@app.errorhandler(401)
def http_401(err):
    response = {
        'code': 401,
        'status': 'unauthorized',
        'message': str(err)
    }
    return flask.jsonify(response), response['code']

@app.errorhandler(403)
def http_403(err):
    response = {
        'code': 403,
        'status': 'forbidden',
        'message': str(err)
    }
    return flask.jsonify(response), response['code']

@app.errorhandler(404)
def http_404(err):
    response = {
        'code': 404,
        'status': 'fail',
        'message': str(err)
    }
    return flask.jsonify(response), response['code']

@app.errorhandler(405)
def http_405(err):
    response = {
        'code': 405,
        'status': 'fail',
        'message': str(err)
    }
    return flask.jsonify(response), response['code']

@app.errorhandler(409)
def http_409(err):
    response = {
        'code': 409,
        'status': 'fail',
        'message': str(err)
    }
    return flask.jsonify(response), response['code']

@app.errorhandler(422)
def http_422(err):
    response = {
        'code': 422,
        'status': 'fail',
        'message': str(err)
    }
    return flask.jsonify(response), response['code']

@app.errorhandler(Exception)
def http_500(err):
    import traceback
    response = {
        'code': 500,
        'status': 'error',
        'message': traceback.format_exc()
    }
    logging.error(err)
    logging.error(traceback.format_exc())
    return flask.jsonify(response), response['code']

# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/auth
@app.route('/api/auth', methods = ['GET'])
@requiresAuth
def apiAuth():
    auth = flask.request.authorization
    return getUsers(auth.username)

# curl -s -D- -u admin:admin -X POST -d '{"path":"/Andrea/Folder 3","name":"New Folder"}' -H 'Content-type: application/json' http://127.0.0.1:5000/api/folders
@app.route('/api/folders', methods = ['POST'])
@requiresAuth
def apiFolders():
    return addFolder()

# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/folders/
# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/folders/Andrea
# curl -s -D- -u admin:admin -X DELETE http://127.0.0.1:5000/api/folders/Andrea
# curl -s -D- -u admin:admin -X PUT -d '{"path":"/Dainese"}' -H 'Content-type: application/json' http://127.0.0.1:5000/api/folders/Andrea
@app.route('/api/folders/', defaults = {'folder': ''}, methods = ['DELETE', 'GET', 'PUT'])
@app.route('/api/folders/<path:folder>', methods = ['DELETE', 'GET', 'PUT'])
@requiresAuth
def apiFoldersPath(folder = None):
    import os
    # Avoid path traversal
    folder = os.path.join('/', folder)
    if flask.request.method == 'DELETE':
        return deleteFolder(folder)
    if flask.request.method == 'GET':
        return getFolder(folder)
    if flask.request.method == 'PUT':
        return editFolder(folder)

@app.route('/api/labs', methods = ['POST'])
@requiresAuth
def apiLabs():
    return addLab()

# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/labs/Andrea/nat.unl
# curl -s -D- -u admin:admin -X CLOSE http://127.0.0.1:5000/api/labs/Andrea/nat.unl
# curl -s -D- -u admin:admin -X OPEN -d '{"name":"dainese","email":"adainese@example.com","password":"dainese","labels":200}' -H 'Content-type: application/json' http://127.0.0.1:5000/api/labs/Andrea/nat.unl
# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/labs/Andrea/nat.unl/networks
# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/labs/Andrea/nat.unl/networks/1
# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/labs/Andrea/nat.unl/nodes
# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/labs/Andrea/nat.unl/nodes/1
# curl -s -D- -u admin:admin -X START http://127.0.0.1:5000/api/labs/Andrea/nat.unl/nodes/1
# curl -s -D- -u admin:admin -X STOP http://127.0.0.1:5000/api/labs/Andrea/nat.unl/nodes/1
@app.route('/api/labs/<path:lab>', methods = ['CLOSE', 'DELETE', 'GET', 'OPEN', 'POST', 'PUT', 'START', 'STOP'])
@requiresAuth
def apiLabsPath(lab = None):
    import os
    # Avoid path traversal
    lab = os.path.join('/', lab)
    return manageLab(lab, flask.request.method)

# Create lab
# curl -s -D- -u admin:admin -X POST -d '{"path":"/Andrea/Folder 3","name":"New Folder"}' -H 'Content-type: application/json' http://127.0.0.1:5000/api/folders
# Open lab
# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/labs/Andrea/Lab%201.unl
# Read lab info -> SQL
# Close lab
# Delete lab
# Edit lab

#$app -> get('/api/labs/(:path+)', function($path = array()) use ($app, $db) {
#$app -> put('/api/labs/(:path+)', function($path = array()) use ($app, $db) {
#$app -> post('/api/labs', function() use ($app, $db) {
#$app -> post('/api/labs/(:path+)', function($path = array()) use ($app, $db) {
#$app -> delete('/api/labs/close', function() use ($app, $db) {
#$app -> delete('/api/labs/(:path+)', function($path = array()) use ($app, $db)


# curl -s -D- -u admin:admin -X PUT -d '{"path":"/Dainese"}' -H 'Content-type: application/json' http://127.0.0.1:5000/api/folders/Andrea
# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/users
# curl -s -D- -u admin:admin -X POST -d '{"name":"andrea","email":"andrea.dainese@example.com","username":"andrea","password":"andrea"}' -H 'Content-type: application/json' http://127.0.0.1:5000/api/users
@app.route('/api/users', methods = ['GET', 'POST'])
@requiresAuth
@requiresRoles('admin')
def apiUsers():
    if flask.request.method == 'GET':
        return getUsers()
    if flask.request.method == 'POST':
        return addUser()

# curl -s -D- -u admin:admin -X DELETE http://127.0.0.1:5000/api/users/andrea
# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/users/andrea
# curl -s -D- -u admin:admin -X PUT -d '{"name":"dainese","email":"adainese@example.com","password":"dainese","labels":200}' -H 'Content-type: application/json' http://127.0.0.1:5000/api/users/andrea
@app.route('/api/users/<username>', methods = ['DELETE', 'GET', 'PUT'])
@requiresAuth
@requiresRoles('admin')
def apiUsersUsername(username):
    if flask.request.method == 'DELETE':
        return deleteUser(username)
    if flask.request.method == 'GET':
        return getUsers(username)
    if flask.request.method == 'PUT':
        return editUser(username)

# curl -s -D- -u admin:admin -X GET http://127.0.0.1:5000/api/refresh
@app.route('/api/refresh', methods = ['GET'])
@requiresAuth
@requiresRoles('admin')
def apiRefresh():
    return refreshDb()

if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5000, debug = True)
