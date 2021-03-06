$(document).ready(function () {
    var loading = '<img src="' + sbRoot + '/images/loading16.gif" height="16" width="16" />';

    /*************************** Pushbullet ***************************/

    if (!$("#pushbullet_apikey").val()) {
        $("#divbullet_devices").hide();
    }
    else {
        PushBullet_Select();
        $( "#divbullet_devices" ).show();
    }

    function PushBullet_Select() {
        var pushbullet_apikey = $("#pushbullet_apikey").val();
        var pushbullet_device = $("#pushbullet_device").val();
        var $select = $('#bullet_devices');

        $.getJSON(sbRoot + "/home/Pushbullet_retriveDevices",  {'apiKey': pushbullet_apikey}, function(data){
            //clear the current content of the select
            $select.html('');

            //populate first value with blank value
            if (data.devices.length) {
                $select.append('<option value="">All Devices</option>');
            }

            //iterate over the data and append a select option
            $.each(data.devices, function(key, val){
                $select.append('<option value="' + val.iden + '">' + val.nickname + '</option>');
                if ($("#pushbullet_device").val()==val.iden) {
                    $select.val(val.iden);
                }
            })
        });
    }

    $('#savePushbullet').click(function () {
        if (!$("#pushbullet_apikey").val()) {
            $('#divbullet_devices').hide("slow");
        }
        else {
            $("#pushbullet_device").val($("#bullet_devices option:selected").val());
            PushBullet_Select();
            $('#divbullet_devices').show("slow");
        }
    });

    $('#testPushbullet').click(function ()
    {
        $('#testPushbullet-result').html(loading);
        var pushbullet_apikey = $("#pushbullet_apikey").val();
        var pushbullet_device = $("#bullet_devices option:selected").val();
        $.get(sbRoot + "/home/testPushbullet", {'apiKey': pushbullet_apikey, 'device': pushbullet_device },
            function (data)
            { $('#testPushbullet-result').html(data); });
    });

    /*************************** EOF Pushbullet ***************************/

    $('#testGrowl').click(function () {
        $('#testGrowl-result').html(loading);
        var growl_host = $("#growl_host").val();
        var growl_password = $("#growl_password").val();
        $.get(sbRoot + "/home/testGrowl", {'host': growl_host, 'password': growl_password},
            function (data) { $('#testGrowl-result').html(data); });
    });

    $('#testProwl').click(function () {
        $('#testProwl-result').html(loading);
        var prowl_api = $("#prowl_api").val();
        var prowl_priority = $("#prowl_priority").val();
        $.get(sbRoot + "/home/testProwl", {'prowl_api': prowl_api, 'prowl_priority': prowl_priority},
            function (data) { $('#testProwl-result').html(data); });
    });

    $('#testXBMC').click(function () {
        $("#testXBMC").attr("disabled", true);
        $('#testXBMC-result').html(loading);
        var xbmc_host = $("#xbmc_host").val();
        var xbmc_username = $("#xbmc_username").val();
        var xbmc_password = $("#xbmc_password").val();
        $.get(sbRoot + "/home/testXBMC", {'host': xbmc_host, 'username': xbmc_username, 'password': xbmc_password})
            .done(function (data) {
                $('#testXBMC-result').html(data);
                $("#testXBMC").attr("disabled", false);
            });
    });

    $('#testPLEX').click(function () {
        $('#testPLEX-result').html(loading);
        var plex_host = $("#plex_host").val();
        var plex_username = $("#plex_username").val();
        var plex_password = $("#plex_password").val();
        $.get(sbRoot + "/home/testPLEX", {'host': plex_host, 'username': plex_username, 'password': plex_password},
            function (data) { $('#testPLEX-result').html(data); });
    });

    $('#testBoxcar').click(function () {
        $('#testBoxcar-result').html(loading);
        var boxcar_username = $("#boxcar_username").val();
        $.get(sbRoot + "/home/testBoxcar", {'username': boxcar_username},
            function (data) { $('#testBoxcar-result').html(data); });
    });

    $('#testPushover').click(function () {
        $('#testPushover-result').html(loading);
        var pushover_userkey = $("#pushover_userkey").val();
        $.get(sbRoot + "/home/testPushover", {'userKey': pushover_userkey},
            function (data) { $('#testPushover-result').html(data); });
    });

    $('#testLibnotify').click(function () {
        $('#testLibnotify-result').html(loading);
        $.get(sbRoot + "/home/testLibnotify",
            function (data) { $('#testLibnotify-result').html(data); });
    });

    $('#twitterStep1').click(function () {
        $('#testTwitter-result').html(loading);
        $.get(sbRoot + "/home/twitterStep1", function (data) {window.open(data); })
            .done(function () { $('#testTwitter-result').html('<b>Step1:</b> Confirm Authorization'); });
    });

    $('#twitterStep2').click(function () {
        $('#testTwitter-result').html(loading);
        var twitter_key = $("#twitter_key").val();
        $.get(sbRoot + "/home/twitterStep2", {'key': twitter_key},
            function (data) { $('#testTwitter-result').html(data); });
    });

    $('#testTwitter').click(function () {
        $.get(sbRoot + "/home/testTwitter",
            function (data) { $('#testTwitter-result').html(data); });
    });

    $('#authorizeTrakt').click(function() {
    $('#testTrakt-result').text('Authenticating...');
        var pin = $('#trakt_pin').val();
        if (pin && pin.trim().length == 8) {
            $.post(sbRoot + '/home/authorizeTrakt', {'pin': pin},
                function (ret) {
                    var data = JSON.parse(ret);
                    $('#trakt_access_token').val(data.result ? data.access_token : '');
                    $('#trakt_refresh_token').val(data.result ? data.refresh_token : '');
                    $('#testTrakt-result').text(data.result ? 'Authorized' : 'Not Authorized');
                    $('#trakt_pin').val('');
                });
        } else {
            $('#testTrakt-result').text('Invalid PIN inserted.');
        }
    });

    $('#settingsNMJ').click(function () {
        if (!$('#nmj_host').val()) {
            alert('Please fill in the Popcorn IP address');
            $('#nmj_host').focus();
            return;
        }
        $('#testNMJ-result').html(loading);
        var nmj_host = $('#nmj_host').val();

        $.get(sbRoot + "/home/settingsNMJ", {'host': nmj_host},
            function (data) {
                if (data === null) {
                    $('#nmj_database').removeAttr('readonly');
                    $('#nmj_mount').removeAttr('readonly');
                }
                var JSONData = $.parseJSON(data);
                $('#testNMJ-result').html(JSONData.message);
                $('#nmj_database').val(JSONData.database);
                $('#nmj_mount').val(JSONData.mount);

                if (JSONData.database) {
                    $('#nmj_database').attr('readonly', true);
                } else {
                    $('#nmj_database').removeAttr('readonly');
                }
                if (JSONData.mount) {
                    $('#nmj_mount').attr('readonly', true);
                } else {
                    $('#nmj_mount').removeAttr('readonly');
                }
            });
    });

    $('#testNMJ').click(function () {
        $('#testNMJ-result').html(loading);
        var nmj_host = $("#nmj_host").val();
        var nmj_database = $("#nmj_database").val();
        var nmj_mount = $("#nmj_mount").val();

        $.get(sbRoot + "/home/testNMJ", {'host': nmj_host, 'database': nmj_database, 'mount': nmj_mount},
            function (data) { $('#testNMJ-result').html(data); });
    });

    $('#settingsNMJv2').click(function () {
        if (!$('#nmjv2_host').val()) {
            alert('Please fill in the Popcorn IP address');
            $('#nmjv2_host').focus();
            return;
        }
        $('#testNMJv2-result').html(loading);
        var nmjv2_host = $('#nmjv2_host').val();
        var nmjv2_dbloc;
        var radios = document.getElementsByName("nmjv2_dbloc");
        for (var i = 0; i < radios.length; i++) {
            if (radios[i].checked) {
                nmjv2_dbloc=radios[i].value;
                break;
            }
        }

        var nmjv2_dbinstance=$('#NMJv2db_instance').val();
        $.get(sbRoot + "/home/settingsNMJv2", {'host': nmjv2_host, 'dbloc': nmjv2_dbloc, 'instance': nmjv2_dbinstance},
        function (data){
            if (data == null) {
                $('#nmjv2_database').removeAttr('readonly');
            }
            var JSONData = $.parseJSON(data);
            $('#testNMJv2-result').html(JSONData.message);
            $('#nmjv2_database').val(JSONData.database);

            if (JSONData.database) {
                $('#nmjv2_database').attr('readonly', true);
            } else {
                $('#nmjv2_database').removeAttr('readonly');
            }
        });
    });

    $('#testNMJv2').click(function () {
        $('#testNMJv2-result').html(loading);
        var nmjv2_host = $("#nmjv2_host").val();

        $.get(sbRoot + "/home/testNMJv2", {'host': nmjv2_host},
            function (data){ $('#testNMJv2-result').html(data); });
    });

    $('#testNMA').click(function () {
        $('#testNMA-result').html(loading);
        var nma_api = $("#nma_api").val();
        var nma_priority = $("#nma_priority").val();
        $.get(sbRoot + "/home/testNMA", {'nma_api': nma_api, 'nma_priority': nma_priority},
            function (data) { $('#testNMA-result').html(data); });
    });
});
