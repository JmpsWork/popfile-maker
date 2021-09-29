# JSON Documentation

This md file contains an explanation as to what all the possible keys does for every json file used by the program.

## config_class.json

* ``classname`` - The name of this class.
  * ``health`` - The base health of this class.
  * ``health_giant`` - The base health of the giant version of this class.
  * ``power`` - The base power of this class. Must be greater than 0.
  * ``speed`` - The speed of this class.
  * ``power_mult_skill`` - A list of 4 floats, each corresponding to a multiplier for the skill of a class from easy to expert.
  * ``power_mult_weapon`` - A list of 3 floats, each corresponding to a multiplier for the weapon slot, starting with primary, then secondary, then melee.
  * ``primaries`` - A list of primary weapons that this class is allowed to use.
    * ``name`` - The name of this weapon.
    * ``weight`` - The chance that this weapon will be used relative to others.
    * ``passive`` - Allows this weapon to be used in parallel with another weapon, and will prevent this weapon from being chosen as the main weapon.
    * ``charge`` - Tells the program that this weapon is compatible with Attributes SpawnWithFullCharge
    * ``alt`` - A list of alternate names for this weapon.
  * ``secondaries`` - A list of secondary weapons that this class is allowed to use.
  * ``melee`` - A list of melee weapons that this class is allowed to use.

## config_attributes.json

* ``attribute_defines`` - A list containing all attributes which can be interpreted by the program in some way.
  * ``name`` - The name of this attribute.
  * ``type`` - What value does this attribute modify? Can either be power, endurance or strength
  * ``inverse`` - The name of this attribute when it tends towards 0.
  * ``operator`` - How the value of this attribute acts upon the power, endurance or strength of a bot. Can either be ``exp``, ``inv_exp``, ``mult``, ``add`` or ``none``
  * ``base`` - Base modifier amount.
  * ``mult`` - A multiplier to the base amount.
  * ``clamp`` - Used when calculating the strength of a bot. If the value goes below this amount, then it will get interpreted as this value instead.
  * ``ceil`` - Identical to clamp, except it checks for any value above this amount.
  * ``def`` - The default value of this attribute.
  * ``alt`` - A list of alternate names for this attribute.
  * ``ca`` - If this attribute should be used in CharaterAttributes.
* ``classname`` - The name of this class.
  * ``attributes_primary`` - A list of attributes this class can use for their primary weapons.
    * ``name`` - The name of the referenced attribute.
    * ``min`` - The minimum value this attribute can have.
    * ``max`` - The maximum value this attribute can have.
    * ``step`` - Every possible value between min and max starting from min. Cannot be 0. 
  * ``attributes_secondary`` - A list of attributes this class can use for their primary weapons.
  * ``attributes_melee`` - A list of attributes this class can use for their primary weapons.
  * ``whitelist_primary`` - A list of attribute referenced in ``attributes_primary`` which can be used for primary weapons.
  * ``whitelist_secondary`` - A list of attribute referenced in ``attributes_primary`` which can be used for primary weapons.
  * ``whitelist_melee`` - A list of attribute referenced in ``attributes_primary`` which can be used for primary weapons.
  * ``items`` - A list of items for this class.
    * ``itemname`` - The name of this item.
      * ``default`` - The default attributes of this item.
      * ``whitelist_extend`` - Extend the whitelist of this weapon's slot with another attribute found within the corresponding attributes for this slot.
      * ``whitelist`` - Override the exisitng whitelist for this slot with a new list of attributes.
      * ``priority`` - A list of attribute names which will be chosen first over others when making a tfbot with this weapon.
      * ``power_base`` - Override the base power of a class with this number. Useful for weaker weapons or passive weapons.
      * ``power_mult`` - The final power of a weapon will get multiplied by this value.
      * ``override`` - Override one or multiple attribute potential values. Useful for weapons which need extreme attribute values to make it useful.

## config_waves.json

* ``pattern`` - Contains specific reoccuring rules for waves.
  * ``every`` - This pattern occurs every X wave.
    * ``X`` - The number of this wave.
      * ``conds`` - A set of conditions for this rule to apply.
      * ``rules`` - If the conditions are true, these rules will apply for this wave.
  * ``range`` - A list of conditions applying if the wave number is within a specific range. First index is the start of the range, second index is the end of the range, and the third index are the rules to apply.
* ``individual`` - This rule wipll apply to this specific wave.
  * ``X`` - The number of this wave.
    * ``rules`` - The rules to apply for this wave. 

**conds**
* ``starting_from`` - The number to consider this pattern from.

**rules**
* ``power_mult_max`` - A multiplier to the maxmimum power that bots can have for this wave.
* ``endurance_mult_max`` - A multiplier to the maxmimum edurance that bots can have for this wave.
* ``strength_mult_max`` - A multiplier to the maxmimum strength that bots can have for this wave.
* ``cash_mult_max`` - A multiplier to the cash provided this wave.
* ``power_add`` - The amount of power to add to this wave.
* ``endurance_add`` - The amount of power to add to this wave.
* ``strength_add`` - The amount of power to add to this wave.
* ``cash_add`` - The amount of power to add to this wave.
* ``no`` - A list of bots which cannot be used for this wave. Can contain ``commons``, ``giants``, ``tanks`` or ``boss``.
* ``must_include`` - A list of bots which must be included in this wave, at least once. Can contain ``commons``, ``giants``, ``tanks`` or ``boss``.
* ``subwaves`` - Override the amount of subwaves (groups of identically named wavespawns) which can be used this wave.
* ``bot_amount`` - The amount of bots which can be used this wave.
* ``bot_types`` - The amount of unique wavespawns which can be used this wave.
* ``custom_only`` - The program will exclusively create new tfbots instead of opting to use ones found inside its templates.

## config_ai.json

* ``max_waves`` - The desired amount of waves which will be created for this mission.
* ``max_subwaves`` - The max amount of wavespawn groups which are allowed per wave.
* ``max_wavespawns`` - Within each subwave group, this is the maximum allowed amount of subwaves which can be used.
* ``bot_passive_chance`` - When making a new bot, this is the chance that it will be allowed to have a passive weapon. Must be a value between ``0`` and ``1``.
* ``bot_minigiant_chance`` - When making a new bot with a strength above ``bot_hp_threshold``, this is the chance that it will be chosen to be a minigiant.
* ``bot_hp_threshold`` - The minimum strength of a bot to be eligble for minigiant status.
* ``bot_giant_hp_threshold`` - The minimum strength where a giant's bot total strength will be split evenly between endurance and power.
* ``bot_deviance_chance`` - When making a new bot, this is the chance that an attribute value will be chosen at random instead of logically.
* ``bot_deviance_max`` - The maximum number of 'deviant' attributes a robot can have.
* ``bot_common_chance`` - When making a subwave, this is the weight that a common robot type will be chosen.
* ``bot_giant_chance`` - When making a subwave, this is the weight that a giant robot type will be chosen.
* ``bot_tank_chance`` - When making a subwave, this is the weight that a tank will be chosen.
* ``bot_boss_chance`` - When making a subwave, this is the weight that a boss robot type will be chosen.
* ``wavespawn_regular_weight`` - When making a subwave, this is the weight that a regular wavespawn (with only one bot type) will be chosen.
* ``wavespawn_random_weight`` - When making a subwave, this is the weight that RandomChoice will be chosen as the spawner.
* ``wavespawn_squad_weight`` - When making a subwave, this is the weight that Squad will be chosen as the spawner.
* ``strength_variance`` - A range of the strength multiplied and divided by this value will be applied to the ideal strength of a subwave. A bot from templates can be chosen from within this range.
* ``endless`` - If set to true, separate waves will instead be merged together instead of split among separate waves.
 
