import asyncio
import aiohttp
import json
from colorama import init, Fore, Style
import os
from typing import Dict, Optional, List
from collections import deque

# Initialize colorama for colored output
init()

class BalanceChecker:
    def __init__(self, input_file: str, empty_file: str, balance_file: str, api_url: str, max_concurrent: int = 5):
        self.input_file = input_file
        self.empty_file = empty_file
        self.balance_file = balance_file
        self.api_url = api_url
        self.max_concurrent = max_concurrent
        self.address_queue = deque()
        self.processed_addresses = []

    async def check_balance(self, session: aiohttp.ClientSession, address: str) -> Optional[Dict]:
        """Make API call to check balance with error handling"""
        try:
            async with session.get(f"{self.api_url}{address}") as response:
                if response.status == 200:
                    return await response.json(), address
                return None, address
        except Exception as e:
            print(f"Error checking address {address}: {str(e)}")
            return None, address

    async def process_batch(self, addresses: List[str]) -> List[tuple]:
        """Process a batch of addresses concurrently"""
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=self.max_concurrent)) as session:
            tasks = [self.check_balance(session, address) for address in addresses]
            return await asyncio.gather(*tasks)

    def update_files(self, results: List[tuple]):
        """Update files based on processing results"""
        addresses_to_remove = set()
        
        for result, address in results:
            if result is None:
                continue

            addresses_to_remove.add(address)
            
            if result['status'] == 'success':
                balance = float(result['data']['balance'])
                
                if balance > 0:
                    with open(self.balance_file, 'a') as f:
                        f.write(f"{address}\n")
                    print(f"{Fore.GREEN}{Style.BRIGHT}Found balance {balance} BTC in address: {address}{Style.RESET_ALL}")
                else:
                    with open(self.empty_file, 'a') as f:
                        f.write(f"{address}\n")

        # Remove processed addresses from input file
        if addresses_to_remove:
            with open(self.input_file, 'r') as f:
                addresses = f.readlines()
            
            with open(self.input_file, 'w') as f:
                f.writelines([addr for addr in addresses if addr.strip() not in addresses_to_remove])

    async def process_file(self):
        """Process the input file and categorize addresses"""
        if not os.path.exists(self.input_file):
            print(f"Input file {self.input_file} not found!")
            return

        while True:
            # Read addresses
            with open(self.input_file, 'r') as f:
                addresses = [line.strip() for line in f.readlines()[:self.max_concurrent]]

            if not addresses:
                print("All addresses processed!")
                break

            # Process batch
            results = await self.process_batch(addresses)
            
            # Update files
            self.update_files(results)

def main():
    # Configuration
    INPUT_FILE = "unchecked.txt"
    EMPTY_FILE = "checked_empty.txt"
    BALANCE_FILE = "checked_balance.txt"
    API_URL = "RequestAccessFrom:api[&#64;]sfweb.ca"  # Replace with your API endpoint
    MAX_CONCURRENT = 5

    # Create checker instance
    checker = BalanceChecker(INPUT_FILE, EMPTY_FILE, BALANCE_FILE, API_URL, MAX_CONCURRENT)
    
    # Run the async process
    asyncio.run(checker.process_file())

if __name__ == "__main__":
    main()
