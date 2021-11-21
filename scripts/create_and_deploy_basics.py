"""
Script to deploy contract and use the basic function of it and basic ERC1155 operations
"""
import time
from scripts.functions import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    fund_with_link,
    get_account,
    get_contract,
)
from brownie import StakeToken, config, network, accounts, LinkToken
from dotenv import load_dotenv


MINT_BRONZE = 10 ** 9
MINT_SILVER = 10 ** 6
MINT_GOLD = 10 ** 3


def create_and_mint(_bronze, _silver, _gold):
    """
    Returns deployed ERC1155 contract and mint initial supply of some basic tokens
    """
    account = get_account()

    contract = StakeToken.deploy(
        get_contract("vrf_coordinator").address,
        get_contract("link_token").address,
        config["networks"][network.show_active()]["fee"],
        config["networks"][network.show_active()]["keyhash"],
        _bronze,
        _silver,
        _gold,
        {"from": account},
        publish_source=config["networks"][network.show_active()].get("verify", False),
    )

    caddr = contract.address

    print(f"Contract deployed at: {caddr}")

    return contract


def transfer_from_contract(to, token_id, amount):
    contract = StakeToken[-1]
    caddr = contract.address
    owner = contract.owner()
    tx = contract.safeTransferFrom(owner, to, token_id, amount, "0x0", {"from": owner})
    tx.wait(1)
    return tx


def balances(account):
    """
    Checks balance of first three tokens
    """
    contract = StakeToken[-1]
    caddr = contract.address
    balanceCall = contract.balanceOfBatch(
        [account, account, account], [0, 1, 2], {"from": account}
    )
    print(balanceCall)


def timed_stake():
    """
    Starts timed stake
    """
    contract = StakeToken[-1]
    caddr = contract.address

    owner = accounts.at(contract.owner())
    tx_start = contract.start_timed_stake(1, {"from": owner})

    tx_enter = [
        contract.enter_timed_stake(0, 100, {"from": accounts[0]}),
        contract.enter_timed_stake(0, 100, {"from": accounts[1]}),
        contract.enter_timed_stake(0, 100, {"from": accounts[2]}),
    ]
    time.sleep(1)
    tx_get_link = fund_with_link(contract.address)
    tx_get_link.wait(1)
    tx_end = contract.end_timed_stake({"from": owner})


def fund_test():
    contract = StakeToken[-1]
    contract.fundLINK(1 * 10 ** 18, {"from": get_account()})


def main():
    """
    Launches all functions implemented above
    """
    contract = create_and_mint(MINT_BRONZE, MINT_SILVER, MINT_GOLD)
