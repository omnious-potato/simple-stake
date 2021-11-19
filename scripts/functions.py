from brownie import (
    accounts,
    network,
    config,
    VRFCoordinatorMock,
    LinkToken,
    Contract,
    interface,
)

FORKED_LOCAL_ENVIRONMENTS = ["mainnet-fork", "mainnet-fork-dev"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development", "ganache-local", "ganache"]
OPENSEA_HEADER = "htpps://testnets.opensea.io/assets/{}/{}"


def get_account(index=0, id=None):
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        return accounts[index]
    if id:
        return accounts.load(id)
    if network.show_active() in config["networks"]:
        if index == 0:
            return accounts.add(config["wallets"]["from_key"])
        if index == 1:
            return accounts.add(config["wallets"]["user_first_key"])
        if index == 2:
            return accounts.add(config["wallets"]["user_second_key"])
    return None


contract_to_mock = {
    "vrf_coordinator": VRFCoordinatorMock,
    "link_token": LinkToken,
}


def get_contract(contract_name):

    contract_type = contract_to_mock[contract_name]
    if network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        if len(contract_type) <= 0:
            deploy_mocks()
        contract = contract_type[-1]
    else:
        contract_address = config["networks"][network.show_active()][contract_name]
        contract = Contract.from_abi(
            contract_type._name, contract_address, contract_type.abi
        )
    return contract


def deploy_mocks():
    print(f"Current network is {network.show_active()}")
    print("Deploying mocks!")

    account = get_account()

    print("Deploying mock LINK token...")
    link_token = LinkToken.deploy({"from": account})
    print(f"LINK token deployed at {link_token.address}")

    print("Deploying mock VRF Coordinator...")
    vrf_coord = VRFCoordinatorMock.deploy(link_token.address, {"from": account})
    print(f"VRF Coordinator deployed at {vrf_coord.address}")

    print("All mocks are deployed!")


def fund_with_link(
    contract_address, account=None, link_token=None, amount=100000000000000000
):  # 0.1 LINK
    account = account if account else get_account()
    link_token = link_token if link_token else get_contract("link_token")
    tx = link_token.transfer(contract_address, amount, {"from": account})
    # link_token_contract = interface.LinkTokenInterface(link_token.address)
    # tx = link_token_contract.transfer(contract_address, amount, {"from": account})
    tx.wait(1)
    print("Fund contract!")
    return tx
