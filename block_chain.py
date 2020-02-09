import json
import hashlib
import sys
import requests
from time import time
from uuid import uuid4
from urllib.parse import urlparse
from flask import Flask, jsonify, request


class BlockChain:
    def __init__(self):
        """Defines a block chain on one machine"""
        self.chain = []
        self.current_transactions = []
        self.nodes = set()
        self.new_block(proof=100, previous_hash=1)

    def register_node(self, address):
        """Give us the address of each node """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """Check if the chain is valid"""
        last_block = chain[0]
        current_index = 1
        while current_index < len(chain):
            block = chain[current_index]
            if block['previous_hash'] != self.hash(last_block):
                return False
            if not self.valid_proof(self.hash(last_block), block['proof']):
                return False

            last_block = block
            current_index += 1
        return True

    def resolve_conflicts(self):
        """  This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network."""

        neighbours = self.nodes
        new_chain = None
        max_length = len(self.chain)

        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash=None):
        """Create new block and add it to the chain"""

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(all_blocks_string)
        }

        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        """Add new transaction to the list of transactions (mempool)"""
        self.current_transactions.append({'sender': sender, 'recipient': recipient, 'amount': amount})
        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """Hashes of block"""
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """Return the last block in the chain """
        return self.chain[-1]

    @staticmethod
    def valid_proof(previous_hash, proof):
        """Checks if this proof is fine or not"""

        guess = f'{previous_hash}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == '0000'

    def proof_of_work(self, previous_hash):
        """Shows the work is done"""
        proof = 0
        while self.valid_proof(previous_hash, proof) is False:
            proof += 1
        return proof


app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')
block_chain = BlockChain()


@app.route('/mine', methods=['GET'])
def mine():
    """This will mine and  will add it to the chain"""
    last_block = block_chain.last_block
    previous_hash = block_chain.hash(last_block)
    proof = block_chain.proof_of_work(previous_hash)

    block_chain.new_transaction(sender='0', recipient=node_identifier, amount=50)
    block = block_chain.new_block(proof, previous_hash)
    response = {
        'message': 'New block forged',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    """This will add new transactions by getting sender, recipient and amount"""
    values = request.get_json()
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    new_trx = block_chain.new_transaction(values['sender'], values['recipient'], values['amount'])
    response = {'message': f'Transaction will be added to Block {new_trx}'}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    """This will show us the full chain"""
    response = {
        'chain': block_chain.chain,
        'length': len(block_chain.chain),
    }
    return jsonify(response), 200


@app.route('/nodes/register', methods=['POST'])
def register_node():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        block_chain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(block_chain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = block_chain.resolve_conflicts()
    if replaced:
        response = {
            'message': 'New chain was replaced',
            'chain': block_chain.chain
        }

    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': block_chain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=sys.argv[1])
