#!/bin/bash

# Termux System Information Tool (fastfetch-like)
# Works without root access

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[0;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ASCII Art (Android robot)
print_logo() {
    echo -e "${GREEN}"
    echo "    o- "
    echo "   +mMMMMMMMMMMMMm+"
    echo "  \`dMMm:NMMMMMMN:mMMd\`"
    echo "  hMMMMMMMMMMMMMMMMMMh"
    echo "  yyyyyyyyyyyyyyyyyyyy"
    echo " .mMMm\`MMMMMMMMMMMMMMMMMMMM\`mMMm."
    echo " :MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM:"
    echo " :MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM:"
    echo " :MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM:"
    echo " :MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM:"
    echo " -MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM-"
    echo " +yy+ MMMMMMMMMMMMMMMMMMMM +yy+"
    echo " ]mMMMMMMMMMMMMMMMMMMm["
    echo " \`/++MMMMh++hMMMM++/\`"
    echo "     MMMMo oMMMM"
    echo "     ]MMMMo oMMMM["
    echo "      eoNMm- -mMNs"
    echo -e "${NC}"
}

# Get username and hostname
get_user_host() {
    echo -e "${CYAN}${USER}@$(hostname)${NC}"
}

# Get OS information
get_os() {
    if [ -f /system/build.prop ]; then
        android_version=$(getprop ro.build.version.release 2>/dev/null || echo "Unknown")
        arch=$(uname -m)
        echo -e "${BOLD}OS:${NC} Android $android_version $arch"
    else
        echo -e "${BOLD}OS:${NC} $(uname -s) $(uname -r) $(uname -m)"
    fi
}

# Get device model
get_host() {
    if command -v getprop >/dev/null 2>&1; then
        manufacturer=$(getprop ro.product.manufacturer 2>/dev/null || echo "Unknown")
        model=$(getprop ro.product.model 2>/dev/null || echo "Unknown")
        echo -e "${BOLD}Host:${NC} $manufacturer $model"
    else
        echo -e "${BOLD}Host:${NC} Unknown"
    fi
}

# Get kernel version
get_kernel() {
    kernel=$(uname -r)
    echo -e "${BOLD}Kernel:${NC} Linux $kernel"
}

# Get uptime
get_uptime() {
    if [ -f /proc/uptime ]; then
        uptime_seconds=$(cut -d. -f1 /proc/uptime)
        hours=$((uptime_seconds / 3600))
        minutes=$(((uptime_seconds % 3600) / 60))
        
        if [ $hours -gt 0 ]; then
            echo -e "${BOLD}Uptime:${NC} ${hours} hours, ${minutes} mins"
        else
            echo -e "${BOLD}Uptime:${NC} ${minutes} mins"
        fi
    else
        echo -e "${BOLD}Uptime:${NC} Unknown"
    fi
}

# Get package count
get_packages() {
    if command -v dpkg >/dev/null 2>&1; then
        count=$(dpkg -l 2>/dev/null | grep -c '^ii')
        echo -e "${BOLD}Packages:${NC} $count (dpkg)"
    elif command -v pkg >/dev/null 2>&1; then
        count=$(pkg list-installed 2>/dev/null | wc -l)
        echo -e "${BOLD}Packages:${NC} $count (pkg)"
    else
        echo -e "${BOLD}Packages:${NC} Unknown"
    fi
}

# Get shell
get_shell() {
    shell_name=$(basename "$SHELL")
    if command -v "$shell_name" >/dev/null 2>&1; then
        shell_version=$("$shell_name" --version 2>/dev/null | head -n1 | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1)
        echo -e "${BOLD}Shell:${NC} $shell_name $shell_version"
    else
        echo -e "${BOLD}Shell:${NC} $shell_name"
    fi
}

# Get terminal
get_terminal() {
    if [ -n "$TERMUX_VERSION" ]; then
        echo -e "${BOLD}Terminal:${NC} Termux"
    elif [ -n "$TERM_PROGRAM" ]; then
        echo -e "${BOLD}Terminal:${NC} $TERM_PROGRAM"
    else
        echo -e "${BOLD}Terminal:${NC} ${TERM:-Unknown}"
    fi
}

# Get CPU information
get_cpu() {
    if [ -f /proc/cpuinfo ]; then
        # Get CPU model
        cpu_model=$(grep -m1 "model name" /proc/cpuinfo | cut -d: -f2 | sed 's/^ *//')
        if [ -z "$cpu_model" ]; then
            cpu_model=$(grep -m1 "Hardware" /proc/cpuinfo | cut -d: -f2 | sed 's/^ *//')
        fi
        
        # Get core count
        cores=$(grep -c "^processor" /proc/cpuinfo)
        
        # Get max frequency (if available)
        max_freq=""
        if [ -f /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq ]; then
            freq_khz=$(cat /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq 2>/dev/null)
            if [ -n "$freq_khz" ]; then
                freq_ghz=$(echo "scale=2; $freq_khz / 1000000" | bc 2>/dev/null || echo "scale=2; $freq_khz / 1000000" | awk '{print $1/1000000}')
                max_freq=" @ ${freq_ghz} GHz"
            fi
        fi
        
        echo -e "${BOLD}CPU:${NC} ${cpu_model:-Unknown} ($cores)${max_freq}"
    else
        echo -e "${BOLD}CPU:${NC} Unknown"
    fi
}

# Get GPU information
get_gpu() {
    if command -v getprop >/dev/null 2>&1; then
        gpu=$(getprop ro.hardware.vulkan 2>/dev/null)
        if [ -z "$gpu" ]; then
            gpu=$(getprop ro.hardware.egl 2>/dev/null)
        fi
        if [ -z "$gpu" ]; then
            gpu="Unknown"
        fi
        echo -e "${BOLD}GPU:${NC} $gpu"
    else
        echo -e "${BOLD}GPU:${NC} Unknown"
    fi
}

# Get memory information
get_memory() {
    if [ -f /proc/meminfo ]; then
        mem_total=$(grep "MemTotal:" /proc/meminfo | awk '{print $2}')
        mem_available=$(grep "MemAvailable:" /proc/meminfo | awk '{print $2}')
        
        if [ -z "$mem_available" ]; then
            mem_free=$(grep "MemFree:" /proc/meminfo | awk '{print $2}')
            mem_cached=$(grep "^Cached:" /proc/meminfo | awk '{print $2}')
            mem_available=$((mem_free + mem_cached))
        fi
        
        mem_used=$((mem_total - mem_available))
        
        # Convert to GiB
        mem_total_gib=$(echo "scale=2; $mem_total / 1048576" | bc 2>/dev/null || awk "BEGIN {printf \"%.2f\", $mem_total/1048576}")
        mem_used_gib=$(echo "scale=2; $mem_used / 1048576" | bc 2>/dev/null || awk "BEGIN {printf \"%.2f\", $mem_used/1048576}")
        
        # Calculate percentage
        mem_percent=$(echo "scale=0; $mem_used * 100 / $mem_total" | bc 2>/dev/null || awk "BEGIN {printf \"%.0f\", $mem_used*100/$mem_total}")
        
        echo -e "${BOLD}Memory:${NC} ${mem_used_gib} GiB / ${mem_total_gib} GiB (${mem_percent}%)"
    else
        echo -e "${BOLD}Memory:${NC} Unknown"
    fi
}

# Get swap information
get_swap() {
    if [ -f /proc/meminfo ]; then
        swap_total=$(grep "SwapTotal:" /proc/meminfo | awk '{print $2}')
        swap_free=$(grep "SwapFree:" /proc/meminfo | awk '{print $2}')
        
        if [ "$swap_total" -gt 0 ] 2>/dev/null; then
            swap_used=$((swap_total - swap_free))
            
            # Convert to GiB
            swap_total_gib=$(echo "scale=2; $swap_total / 1048576" | bc 2>/dev/null || awk "BEGIN {printf \"%.2f\", $swap_total/1048576}")
            swap_used_gib=$(echo "scale=2; $swap_used / 1048576" | bc 2>/dev/null || awk "BEGIN {printf \"%.2f\", $swap_used/1048576}")
            
            # Calculate percentage
            swap_percent=$(echo "scale=0; $swap_used * 100 / $swap_total" | bc 2>/dev/null || awk "BEGIN {printf \"%.0f\", $swap_used*100/$swap_total}")
            
            echo -e "${BOLD}Swap:${NC} ${swap_used_gib} GiB / ${swap_total_gib} GiB (${swap_percent}%)"
        fi
    fi
}

# Get disk usage
get_disk() {
    # Root filesystem
    if command -v df >/dev/null 2>&1; then
        root_usage=$(df -h / 2>/dev/null | tail -n1)
        if [ -n "$root_usage" ]; then
            used=$(echo "$root_usage" | awk '{print $3}')
            total=$(echo "$root_usage" | awk '{print $2}')
            echo -e "${BOLD}Disk (/):${NC} $used / $total"
        fi
        
        # External storage (if available)
        if [ -d "/storage/emulated/0" ]; then
            external_usage=$(df -h /storage/emulated/0 2>/dev/null | tail -n1)
            if [ -n "$external_usage" ]; then
                used=$(echo "$external_usage" | awk '{print $3}')
                total=$(echo "$external_usage" | awk '{print $2}')
                echo -e "${BOLD}Disk (/storage/emulated):${NC} $used / $total"
            fi
        fi
    fi
}

# Get network interfaces
get_network() {
    if command -v ip >/dev/null 2>&1; then
        ip addr show 2>/dev/null | grep -E "inet [0-9]" | grep -v "127.0.0.1" | while read line; do
            ip_addr=$(echo "$line" | awk '{print $2}' | cut -d'/' -f1)
            interface=$(echo "$line" | awk '{print $NF}')
            echo -e "${BOLD}Local IP ($interface):${NC} $ip_addr"
        done
    elif [ -f /proc/net/route ]; then
        # Fallback method
        for interface in /sys/class/net/*; do
            if [ -d "$interface" ]; then
                iface=$(basename "$interface")
                if [ "$iface" != "lo" ] && [ -f "$interface/operstate" ]; then
                    state=$(cat "$interface/operstate" 2>/dev/null)
                    if [ "$state" = "up" ]; then
                        echo -e "${BOLD}Interface:${NC} $iface (up)"
                    fi
                fi
            fi
        done
    fi
}

# Get locale
get_locale() {
    if [ -n "$LANG" ]; then
        echo -e "${BOLD}Locale:${NC} $LANG"
    else
        echo -e "${BOLD}Locale:${NC} Unknown"
    fi
}

# Main function
main() {
    # Info items to display
    info_items=(
        "$(get_user_host)"
        "$(printf '%*s' 17 | tr ' ' '-')"
        "$(get_os)"
        "$(get_host)"
        "$(get_kernel)"
        "$(get_uptime)"
        "$(get_packages)"
        "$(get_shell)"
        "$(get_terminal)"
        "$(get_cpu)"
        "$(get_gpu)"
        "$(get_memory)"
        "$(get_swap)"
        "$(get_disk)"
        "$(get_network)"
        "$(get_locale)"
    )
    
    # Print logo and info side by side
    logo_lines=(
        "    o- "
        "   +mMMMMMMMMMMMMm+"
        "  \`dMMm:NMMMMMMN:mMMd\`"
        "  hMMMMMMMMMMMMMMMMMMh"
        "  yyyyyyyyyyyyyyyyyyyy"
        " .mMMm\`MMMMMMMMMMMMMMMMMMMM\`mMMm."
        " :MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM:"
        " :MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM:"
        " :MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM:"
        " :MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM:"
        " -MMMM-MMMMMMMMMMMMMMMMMMMM-MMMM-"
        " +yy+ MMMMMMMMMMMMMMMMMMMM +yy+"
        " ]mMMMMMMMMMMMMMMMMMMm["
        " \`/++MMMMh++hMMMM++/\`"
        "     MMMMo oMMMM"
        "     ]MMMMo oMMMM["
        "      eoNMm- -mMNs"
    )
    
    max_lines=$(( ${#logo_lines[@]} > ${#info_items[@]} ? ${#logo_lines[@]} : ${#info_items[@]} ))
    
    for ((i=0; i<max_lines; i++)); do
        logo_part=""
        if [ $i -lt ${#logo_lines[@]} ]; then
            logo_part="${GREEN}${logo_lines[$i]}${NC}"
        fi
        
        info_part=""
        if [ $i -lt ${#info_items[@]} ]; then
            info_part="${info_items[$i]}"
        fi
        
        # Pad logo part to consistent width (35 chars)
        printf "%-50s %s\n" "$logo_part" "$info_part"
    done
}

# Run the main function
main
