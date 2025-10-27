"""Create description text files for each Akuma animation folder."""

import os

def create_description_files(animations_dir="akuma_animations"):
    """Create a description.txt file in each animation folder."""
    
    if not os.path.exists(animations_dir):
        print(f"Directory {animations_dir} not found!")
        return
    
    # Move descriptions with common fighting game terminology
    move_descriptions = {
        # Basic Stance and Movement
        "akuma-stance": "Standing idle animation. Akuma's neutral stance with breathing animation.",
        "akuma-crouching": "Crouching stance. Used for low attacks and avoiding high projectiles.",
        "akuma-crouch": "Transition to crouching position.",
        
        # Movement
        "akuma-walkf": "Walking forward animation.",
        "akuma-walkb": "Walking backward animation.",
        "akuma-dashf": "Forward dash. Quick forward movement with brief invincibility frames.",
        "akuma-dashb": "Backward dash. Quick retreat movement.",
        
        # Jumping
        "akuma-jump": "Neutral jump (straight up). Used for avoiding ground attacks.",
        "akuma-jumpf": "Forward jump. Diagonal jump toward opponent.",
        "akuma-jumpb": "Backward jump. Diagonal jump away from opponent.",
        
        # Basic Attacks - Standing
        "akuma-wp": "Standing Light Punch (LP). Fast, short-range jab.",
        "akuma-mp": "Standing Medium Punch (MP). Balanced speed and range punch.",
        "akuma-hp": "Standing Heavy Punch (HP). Slow but powerful punch with good range.",
        "akuma-wk": "Standing Light Kick (LK). Quick, short-range kick.",
        "akuma-mk": "Standing Medium Kick (MK). Mid-range kick with good speed.",
        "akuma-hk": "Standing Heavy Kick (HK). Powerful, long-range kick.",
        
        # Basic Attacks - Close Standing
        "akuma-wpc": "Close Standing Light Punch. Different animation when close to opponent.",
        "akuma-mpc": "Close Standing Medium Punch. Close-range version with different properties.",
        "akuma-hpc": "Close Standing Heavy Punch. Close-range heavy attack.",
        "akuma-mkc": "Close Standing Medium Kick. Close-range version of MK.",
        "akuma-hkc": "Close Standing Heavy Kick. Close-range version of HK.",
        
        # Crouching Attacks
        "akuma-crouch-wp": "Crouching Light Punch. Low jab attack.",
        "akuma-crouch-mp": "Crouching Medium Punch. Low punch with good range.",
        "akuma-crouch-hp": "Crouching Heavy Punch. Anti-air uppercut attack.",
        "akuma-crouch-wk": "Crouching Light Kick. Low kick attack.",
        "akuma-crouch-mk": "Crouching Medium Kick. Mid-range low kick.",
        "akuma-crouch-hk": "Crouching Heavy Kick. Sweep attack that knocks down opponent.",
        
        # Jumping Attacks
        "akuma-jump-wp": "Jumping Light Punch. Air-to-air or jump-in attack.",
        "akuma-jump-mp": "Jumping Medium Punch. Balanced air attack.",
        "akuma-jump-hp": "Jumping Heavy Punch. Powerful jump-in attack.",
        "akuma-jump-wk": "Jumping Light Kick. Quick air kick.",
        "akuma-jump-mk": "Jumping Medium Kick. Cross-up capable air attack.",
        "akuma-jump-hk": "Jumping Heavy Kick. Heavy air attack with good damage.",
        "akuma-jumpf-mk": "Forward Jumping Medium Kick. Diagonal jump attack variation.",
        
        # Special Moves
        "akuma-fireball": "Hadoken (QCF+P). Projectile attack. Speed varies by punch button.",
        "akuma-fireball2": "Red Hadoken (HCB+P). Slower, more damaging projectile.",
        "akuma-dp": "Shoryuken (F,D,DF+P). Anti-air dragon punch with invincibility frames.",
        "akuma-hurricane": "Tatsumaki Senpukyaku (QCB+K). Hurricane kick with multiple hits.",
        "akuma-fmp": "Forward+MP. Overhead attack that hits high.",
        "akuma-overhead": "MP+MK. Universal overhead attack.",
        
        # Advanced Specials
        "akuma-airkick": "Air Tatsumaki (Jump UF->D+K). Air version of hurricane kick.",
        "akuma-teleport": "Ashura Senku (F,D,DF+PPP). Teleport with brief invincibility.",
        "akuma-hyakkishuu": "Hyakkishu (F,D,DF+K). Demon flip with multiple follow-ups.",
        
        # Throws
        "akuma-throw-forward": "Forward Throw (F+LP+LK). Grabs and throws opponent forward.",
        "akuma-throw-back": "Backward Throw (B+LP+LK). Grabs and throws opponent backward.",
        "akuma-throw-miss": "Throw Whiff. Animation when throw attempt misses.",
        "akuma-airthrow": "Air Throw. Grab opponent in mid-air during Hyakkishu.",
        
        # Super Arts
        "akuma-sa1-air": "Messatsu Gou Hadou (QCF,QCF+P) [Air]. Multi-hit projectile super.",
        "akuma-sa2": "Tenma Gou Zanku (QCF,QCF+K). Air fireball super art.",
        "akuma-sa3": "Messatsu Gou Shoryu (QCB,QCB+K). Multi-hit dragon punch super.",
        
        # Secret/Bonus Moves
        "akuma-flame": "Raging Demon Setup (LP,LP,F,MK,HP). Command grab super setup.",
        "akumaragingstorm2": "Shun Goku Satsu (D,D,D+PP). Instant kill super (Raging Demon).",
        
        # Defensive
        "akuma-block": "Standing Block. Defending against mid attacks.",
        "akuma-block-high": "High Block. Defending against overhead attacks.",
        "akuma-block-crouch": "Low Block. Defending against low attacks.",
        "akuma-parry": "Forward Parry. Precise timing defensive technique.",
        "akuma-parry-low": "Low Parry. Parrying low attacks.",
        
        # Hit Reactions
        "akuma-stand-hit": "Standing Hit Stun. Taking damage while standing.",
        "akuma-crouch-hit": "Crouching Hit Stun. Taking damage while crouching.",
        "akuma-shocked": "Stun State. Dizzy/stunned animation.",
        "akuma-slam": "Knockdown. Being slammed to the ground.",
        "akuma-twist": "Spinning Knockdown. Spinning hit reaction.",
        
        # Win/Lose States
        "akuma-intro1": "Round Introduction. Pre-fight entrance animation.",
        "akuma-win1": "Victory Pose 1. First victory animation.",
        "akuma-win2": "Victory Pose 2. Second victory animation.",
        "akuma-win3": "Victory Pose 3. Third victory animation.",
        "akuma-taunt": "Taunt Animation. Provocation move (builds meter in some games).",
        "akuma-timeout": "Time Over. Animation when round timer expires.",
        "akuma-chipdeath": "Chip Death. Defeated by chip damage from blocked special moves.",
    }
    
    created_count = 0
    
    # Get all animation folders
    animation_folders = [d for d in os.listdir(animations_dir) 
                        if os.path.isdir(os.path.join(animations_dir, d))]
    
    print(f"Found {len(animation_folders)} animation folders:")
    
    for folder_name in sorted(animation_folders):
        folder_path = os.path.join(animations_dir, folder_name)
        description_file = os.path.join(folder_path, "description.txt")
        
        # Get description or use default
        description = move_descriptions.get(folder_name, 
            f"Animation: {folder_name}\n\nDescription: [Add your description here]\n\nNotes: [Add any technical notes or frame data here]")
        
        # Create the description file
        with open(description_file, 'w', encoding='utf-8') as f:
            f.write(f"Move: {folder_name}\n")
            f.write("=" * (len(folder_name) + 6) + "\n\n")
            f.write(f"{description}\n\n")
            f.write("Technical Notes:\n")
            f.write("- Frame count: [Count the PNG files in this folder]\n")
            f.write("- Startup frames: [Frames before attack becomes active]\n")
            f.write("- Active frames: [Frames where attack can hit]\n")
            f.write("- Recovery frames: [Frames after attack until neutral]\n")
            f.write("- Damage: [Attack damage value]\n")
            f.write("- Properties: [Special properties like invincibility, knockdown, etc.]\n\n")
            f.write("Animation Files:\n")
            
            # List all PNG files in the folder
            png_files = [f for f in os.listdir(folder_path) if f.endswith('.png')]
            f.write(f"- Total frames: {len(png_files)}\n")
            f.write(f"- Files: {', '.join(sorted(png_files))}\n")
        
        print(f"  ✓ Created description.txt for {folder_name}")
        created_count += 1
    
    print(f"\n✓ Created {created_count} description files!")
    print(f"\nYou can now edit each description.txt file to add your own details about:")
    print("- What the move does")
    print("- How to perform it (input commands)")
    print("- Frame data and technical properties")
    print("- Strategic usage tips")

if __name__ == "__main__":
    create_description_files()
