import re
import hashlib
from Crypto.Hash import keccak

class FinalShellCrack:
    MACHINE_CODE_PATTERN = re.compile(r'^\w+@[a-f0-9]{16}$')

    @staticmethod
    def md5(msg: str) -> str:
        """Calculate MD5 hash of a string and return specific substring."""
        hash_obj = hashlib.md5(msg.encode())
        return hash_obj.hexdigest()[8:24]

    @staticmethod
    def keccak384(msg: str) -> str:
        """Calculate Keccak-384 hash of a string and return specific substring."""
        keccak_hash = keccak.new(digest_bits=384)
        keccak_hash.update(msg.encode())
        return keccak_hash.hexdigest()[12:28]

    @staticmethod
    def is_machine_code(content: str) -> bool:
        """Check if the content matches the machine code pattern."""
        return bool(FinalShellCrack.MACHINE_CODE_PATTERN.match(content))

    @staticmethod
    def crack(code: str) -> str:
        """Generate activation codes for FinalShell."""
        # For version >= 4.5.12 (latest)
        pro_key = FinalShellCrack.keccak384(code + "b(xxkHn%z);x")
        
        return f"版本号 >= 4.5.12 (最新版)\n专业版: {pro_key}" 
    
if __name__ == "__main__":
    print(FinalShellCrack.crack("123@acb33a2715dbfd6d"))